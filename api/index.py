import os
import sys
import types
import socket
import traceback

_log = []

_real_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    supabase_host = os.getenv("DB_HOST", "")
    pooler_host = "aws-0-us-east-1.pooler.supabase.com"
    if supabase_host and host == supabase_host:
        results = _real_getaddrinfo(pooler_host, port, family, type, proto, flags)
        if results:
            return results
    return _real_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _patched_getaddrinfo


def _diag(environ, start_response):
    body = "\n".join(_log).encode()
    start_response("200 OK", [
        ("Content-Type", "text/plain"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


def _init():
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ADMIN_DIR = os.path.join(PROJECT_ROOT, "admin")

    for p in [PROJECT_ROOT, ADMIN_DIR, os.path.dirname(PROJECT_ROOT)]:
        if p not in sys.path:
            sys.path.insert(0, p)

    def _make_package(name, path):
        if name in sys.modules:
            return sys.modules[name]
        mod = types.ModuleType(name)
        mod.__path__ = [path]
        mod.__package__ = name
        mod.__file__ = os.path.join(path, "__init__.py")
        sys.modules[name] = mod
        return mod

    _make_package("AdminClient", PROJECT_ROOT)
    _make_package("AdminClient.admin", ADMIN_DIR)

    for sub in sorted(os.listdir(ADMIN_DIR)):
        sub_path = os.path.join(ADMIN_DIR, sub)
        if os.path.isdir(sub_path) and os.path.exists(os.path.join(sub_path, "__init__.py")):
            _make_package(f"AdminClient.admin.{sub}", sub_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")
    os.environ.setdefault("SCANNER_DATA_DIR", "/tmp")

    import django
    django.setup()

    from django.core.handlers.wsgi import WSGIHandler
    return WSGIHandler()


try:
    _real_app = _init()
except Exception:
    _log.append("INIT_CRASH: " + traceback.format_exc())
    _real_app = None


def application(environ, start_response):
    if environ.get("PATH_INFO", "") == "/__diag":
        return _diag(environ, start_response)
    if _real_app is None:
        return _diag(environ, start_response)
    try:
        return _real_app(environ, start_response)
    except Exception:
        _log.append("REQ_CRASH: " + traceback.format_exc())
        return _diag(environ, start_response)
