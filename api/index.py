import os
import sys
import json
import traceback
import threading
import urllib.request
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
        _init_log.append(f"[OK] DATABASE_URL is set → using PostgreSQL")
    else:
        _init_log.append("[ERROR] DATABASE_URL not set. On Vercel a persistent Postgres is required.")
        # Fail fast so the deployment shows the problem in the logs
        if os.getenv("VERCEL", "0") == "1":
            raise RuntimeError(
                "DATABASE_URL is not set. On Vercel you must provision a managed Postgres "
                "(Supabase, Neon, Railway, Vercel Postgres, …) and add its connection string "
                "as the environment variable DATABASE_URL in the Vercel dashboard."
            )
        _init_log.append("[WARN] Falling back to ephemeral SQLite at /tmp/vercel.db (data will be lost each request)")

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if supabase_url and supabase_key:
        _init_log.append("[OK] SUPABASE_URL and SUPABASE_SERVICE_KEY are set")
        # Register Vercel URL in Supabase for cloud discovery
        vercel_url = os.getenv("VERCEL_URL", "")
        if vercel_url:
            try:
                from supabase import create_client
                
                # Extract hostname from Vercel URL
                if vercel_url.startswith("https://"):
                    hostname = vercel_url[8:]
                elif vercel_url.startswith("http://"):
                    hostname = vercel_url[7:]
                else:
                    hostname = vercel_url
                hostname = hostname.split("/")[0]
                
                supabase = create_client(supabase_url, supabase_key)
                supabase.table("server_registry").upsert({
                    "id": "admin",
                    "ip_address": hostname,
                    "port": 443,
                    "protocol": "https",
                    "is_active": True,
                    "updated_at": "now()",
                }).execute()
                _init_log.append(f"[OK] Registered Vercel URL in Supabase: https://{hostname}")
            except Exception as e:
                err_str = str(e)
                if "Cannot assign requested address" in err_str or "Network is unreachable" in err_str:
                    _init_log.append("[WARN] Supabase registration failed (Vercel network restriction): " + err_str)
                else:
                    _init_log.append(f"[WARN] Failed to register Vercel URL in Supabase: {e}")
    else:
        _init_log.append("[WARN] SUPABASE_URL or SUPABASE_SERVICE_KEY missing → cloud discovery disabled")

    from django.core.management import call_command
    try:
        call_command("migrate", "--run-syncdb", verbosity=0)
        _init_log.append("[OK] Database migrations applied successfully")
    except Exception as e:
        err_detail = traceback.format_exc()
        _init_log.append(f"[ERROR] migrate failed: {e}")
        _init_log.append(f"[ERROR] Detail: {err_detail[:500]}")
        from django.core.wsgi import get_wsgi_application
        _handler = get_wsgi_application()
        _init_log.append("[WARN] App started without DB (pages will show errors until DB is fixed)")
        return

    # Only create default admin user when using a real persistent DB (PostgreSQL)
    if db_url:
        from django.contrib.auth.models import User
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin123")
            _init_log.append("[OK] Default admin user created (username=admin, password=admin123)")
        else:
            _init_log.append("[OK] Admin user already exists")
        
        # Ensure admin client record exists and is linked to superuser (for Vercel)
        try:
            from scanner_api.views import ensure_admin_client
            admin_key = ensure_admin_client()
            _init_log.append(f"[OK] Admin client ensured: {admin_key}")
        except Exception as e:
            _init_log.append(f"[WARN] Admin client setup failed: {e}")
    else:
        _init_log.append("[SKIP] Skipped admin user creation (SQLite /tmp is ephemeral, use Signup instead)")

    from django.apps import apps
    Setting = apps.get_model("scanner_api", "Setting")
    import secrets
    vercel_url = os.getenv("VERCEL_URL", "admin-client-weld.vercel.app")
    Setting.set("admin_server_url", f"https://{vercel_url}")
    
    # Auto-approve clients on Vercel so they don't get stuck in "Checking..."
    if os.getenv("VERCEL", "0") == "1":
        Setting.set("auto_approve", "true")
        _init_log.append("[OK] Auto-approve enabled for Vercel")
    
    if not Setting.get("admin_connection_token", ""):
        Setting.set("admin_connection_token", secrets.token_hex(16))
    _init_log.append("[OK] Settings initialised")

    from django.core.wsgi import get_wsgi_application
    _handler = get_wsgi_application()
    _init_log.append("[OK] App ready")


def _ensure_init():
    global _handler, _init_error
    if _handler is None:
        with _init_lock:
            if _handler is None:
                try:
                    _bootstrap()
                except Exception as e:
                    _init_error = traceback.format_exc()
                    _init_log.append("[FATAL] " + _init_error)


def app(environ, start_response):
    _ensure_init()

    path = environ.get("PATH_INFO", "")

    # Diagnostic endpoint: visit /__diag to see full init log
    if path == "/__diag":
        body = "\n".join(_init_log).encode() if _init_log else b"OK (no log)"
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [body]

    # Health check endpoint: visit /__health to see DB + env status
    if path == "/__health":
        import json as _json
        db_url = os.getenv("DATABASE_URL", "")
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        db_ok = False
        db_error = ""
        if _handler is not None:
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                db_ok = True
            except Exception as e:
                db_error = str(e)
        status = {
            "database_url_set": bool(db_url),
            "supabase_url_set": bool(supabase_url),
            "supabase_key_set": bool(supabase_key),
            "app_initialised": _handler is not None,
            "db_connection_ok": db_ok,
            "db_error": db_error,
            "init_log": _init_log,
        }
        body = _json.dumps(status, indent=2).encode()
        start_response("200 OK", [("Content-Type", "application/json")])
        return [body]

    if _handler is None:
        msg = (_init_error or "App is still initializing, please retry in a moment")[:1000]
        start_response("503 Service Unavailable", [("Content-Type", "text/plain")])
        return [msg.encode()]

    return _handler(environ, start_response)
