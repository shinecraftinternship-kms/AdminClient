import os
import sys
import types
import traceback

_log = []

IS_VERCEL = os.getenv("VERCEL", "0") == "1"


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

    if IS_VERCEL:
        _setup_vercel_db()

    from django.core.handlers.wsgi import WSGIHandler
    return WSGIHandler()


def _setup_vercel_db():
    import django
    from django.core.management import call_command

    try:
        call_command("migrate", "--run-syncdb", verbosity=0)
        _log.append("VERCEL_DB: migrate ok")
    except Exception as e:
        _log.append(f"VERCEL_DB_MIGRATE_ERR: {e}")

    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin123")
            _log.append("VERCEL_DB: created admin superuser")
        else:
            _log.append("VERCEL_DB: admin user exists")
    except Exception as e:
        _log.append(f"VERCEL_DB_USER_ERR: {e}")

    try:
        from scanner_api.views import ensure_admin_client
        ensure_admin_client()
        _log.append("VERCEL_DB: admin client ensured")
    except Exception as e:
        _log.append(f"VERCEL_DB_ADMIN_CLIENT_ERR: {e}")

    try:
        from scanner_api.supabase_client import register_server_in_registry
        register_server_in_registry("admin-client-weld.vercel.app", 443, "https")
        _log.append("VERCEL_DB: registered with cloud discovery")
    except Exception as e:
        _log.append(f"VERCEL_DB_CLOUD_REG_ERR: {e}")


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
