import os
import sys
import json
import traceback
import threading
from io import BytesIO

_handler = None
_init_lock = threading.Lock()
_init_log = []
_init_error = None


def _bootstrap():
    global _handler
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ADMIN_DIR = os.path.join(PROJECT_ROOT, "admin")

    for p in [PROJECT_ROOT, ADMIN_DIR]:
        if p not in sys.path:
            sys.path.insert(0, p)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")
    os.environ.setdefault("SCANNER_DATA_DIR", "/tmp")

    import django
    django.setup()

    from django.core.management import call_command
    call_command("migrate", "--run-syncdb", verbosity=0)
    _init_log.append("migrate ok")

    from django.contrib.auth.models import User
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin123")
        _init_log.append("admin created")

    from scanner_api.models import Setting
    import secrets
    vercel_url = os.getenv("VERCEL_URL", "admin-client-weld.vercel.app")
    Setting.set("admin_server_url", f"https://{vercel_url}")
    if not Setting.get("admin_connection_token", ""):
        Setting.set("admin_connection_token", secrets.token_hex(16))
    _init_log.append("settings done")

    from django.core.wsgi import get_wsgi_application
    _handler = get_wsgi_application()
    _init_log.append("ready")


def _ensure_init():
    global _handler, _init_error
    if _handler is None:
        with _init_lock:
            if _handler is None:
                try:
                    _bootstrap()
                except Exception as e:
                    _init_error = traceback.format_exc()
                    _init_log.append("FAIL: " + _init_error)


def _diag_response(start_response):
    import os
    parts = []
    if _init_log:
        parts.append("=== INIT LOG ===")
        parts.extend(_init_log)
    parts.append("=== ENV ===")
    for k, v in sorted(os.environ.items()):
        if any(s in k.lower() for s in ("key", "secret", "token", "password", "auth", "cred")):
            v = "***"
        parts.append(f"{k}={v}")
    body = "\n".join(parts).encode()
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [body]


def _error_response(start_response, status="503 Service Unavailable"):
    msg = _init_error or "initializing"
    body = f"Service unavailable: {msg}".encode()
    start_response(status, [("Content-Type", "text/plain")])
    return [body]


def app(environ, start_response):
    _ensure_init()
    if environ.get("PATH_INFO") == "/__diag":
        return _diag_response(start_response)
    if _handler is None:
        return _error_response(start_response)
    return _handler(environ, start_response)


def handler(event, context):
    _ensure_init()

    if event.get("path") == "/__diag":
        body = "\n".join(_init_log).encode() if _init_log else b"OK"
        return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": body.decode()}

    if _handler is None:
        msg = _init_error or "initializing"
        return {"statusCode": 503, "headers": {"Content-Type": "text/plain"}, "body": msg[:500]}

    body = event.get("body") or ""
    if isinstance(body, str):
        body = body.encode()
    query = event.get("queryStringParameters") or {}
    qs = "&".join(f"{k}={v}" for k, v in query.items()) if query else ""

    environ = {
        "REQUEST_METHOD": event.get("httpMethod", "GET"),
        "PATH_INFO": event.get("path", "/"),
        "QUERY_STRING": qs,
        "SERVER_NAME": event.get("headers", {}).get("host", "vercel"),
        "SERVER_PORT": "443",
        "HTTP_HOST": event.get("headers", {}).get("host", "vercel"),
        "wsgi.url_scheme": event.get("headers", {}).get("x-forwarded-proto", "https"),
        "wsgi.input": BytesIO(body),
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": True,
        "wsgi.run_once": False,
    }
    for k, v in (event.get("headers") or {}).items():
        environ["HTTP_" + k.upper().replace("-", "_")] = v

    status = [None]
    resp_headers = [None]

    def start_response(s, h):
        status[0] = s
        resp_headers[0] = h

    body_parts = _handler(environ, start_response)
    body_bytes = b"".join(body_parts)

    return {
        "statusCode": int(status[0].split()[0]) if status[0] else 500,
        "headers": {k: v for k, v in (resp_headers[0] or [])},
        "body": body_bytes.decode("utf-8", errors="replace"),
    }

application = app  # alias for WSGI auto-detection
