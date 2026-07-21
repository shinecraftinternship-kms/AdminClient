import os
import sys
import types
import traceback

_log = []


def _diag(environ, start_response):
    body = "\n".join(_log).encode()
    start_response("200 OK", [
        ("Content-Type", "text/plain"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


try:
    _log.append("STEP1")

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ADMIN_DIR = os.path.join(PROJECT_ROOT, "admin")

    for p in [PROJECT_ROOT, ADMIN_DIR, os.path.dirname(PROJECT_ROOT)]:
        if p not in sys.path:
            sys.path.insert(0, p)

    _log.append("STEP2")

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

    _log.append("STEP3 packages")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")
    os.environ.setdefault("SCANNER_DATA_DIR", "/tmp")

    import django
    django.setup()
    _log.append("STEP4 django OK")

    from django.core.handlers.wsgi import WSGIHandler
    _real_app = WSGIHandler()
    _log.append("STEP5 WSGI OK")

    def application(environ, start_response):
        if environ.get("PATH_INFO", "") == "/__diag":
            return _diag(environ, start_response)
        try:
            return _real_app(environ, start_response)
        except Exception:
            _log.append("REQ_CRASH: " + traceback.format_exc())
            return _diag(environ, start_response)

    _log.append("STEP6 READY")

except Exception:
    _log.append("CRASH: " + traceback.format_exc())
    application = _diag
