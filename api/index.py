import os
import sys
import traceback

_init_log = []
_initialized = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DIR = os.path.join(PROJECT_ROOT, "admin")

for p in [PROJECT_ROOT, ADMIN_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")
os.environ.setdefault("SCANNER_DATA_DIR", "/tmp")

import django
django.setup()

from django.core.handlers.wsgi import WSGIHandler
_handler = WSGIHandler()


def _initialize():
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from scanner_api.models import Setting
    import secrets

    _init_log.append("VERCEL_DB: starting migration")
    call_command("migrate", "--run-syncdb", verbosity=0)
    _init_log.append("VERCEL_DB: migrate ok")

    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin123")
        _init_log.append("VERCEL_DB: admin created")
    else:
        _init_log.append("VERCEL_DB: admin exists")

    vercel_url = os.getenv("VERCEL_URL", "admin-client-weld.vercel.app")
    server_url = f"https://{vercel_url}"
    Setting.set("admin_server_url", server_url)
    _init_log.append(f"VERCEL_DB: url set to {server_url}")

    if not Setting.get("admin_connection_token", ""):
        Setting.set("admin_connection_token", secrets.token_hex(16))
        _init_log.append("VERCEL_DB: token set")

    _init_log.append("VERCEL_DB: initialization complete")


def application(environ, start_response):
    global _initialized

    path = environ.get("PATH_INFO", "")

    if path == "/__diag":
        body = "\n".join(_init_log).encode() if _init_log else b"OK"
        start_response("200 OK", [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(body))),
        ])
        return [body]

    if not _initialized:
        try:
            _initialize()
            _initialized = True
        except Exception as e:
            _init_log.append("INIT_CRASH: " + traceback.format_exc())
            body = (
                "Server initializing... please refresh in a moment.\n"
                "Error: " + str(e)[:200]
            ).encode()
            start_response("503 Service Unavailable", [
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(body))),
            ])
            return [body]

    return _handler(environ, start_response)
