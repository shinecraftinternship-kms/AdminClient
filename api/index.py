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

    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        _init_log.append(f"DATABASE_URL is set, resolves to host in URL")
    else:
        _init_log.append("DATABASE_URL not set, will use SQLite")

    from django.core.management import call_command
    try:
        call_command("migrate", "--run-syncdb", verbosity=0)
        _init_log.append("migrate ok")
    except Exception as e:
        _init_log.append(f"migrate skipped: {e}")
        from django.core.wsgi import get_wsgi_application
        _handler = get_wsgi_application()
        _init_log.append("ready (no db)")
        return

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


def app(environ, start_response):
    _ensure_init()

    if environ.get("PATH_INFO") == "/__diag":
        body = "\n".join(_init_log).encode() if _init_log else b"OK"
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [body]

    if _handler is None:
        msg = _init_error or "initializing"
        start_response("503 Service Unavailable", [("Content-Type", "text/plain")])
        return [msg[:500].encode()]

    return _handler(environ, start_response)
