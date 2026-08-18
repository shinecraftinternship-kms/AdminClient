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
        if os.getenv("VERCEL", "0") == "1":
            _init_log.append("[WARN] DATABASE_URL not set on Vercel. Falling back to ephemeral SQLite (data lost each request). Set DATABASE_URL in Vercel dashboard for persistence.")
        else:
            _init_log.append("[WARN] DATABASE_URL not set. Falling back to local SQLite.")

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if supabase_url and supabase_key:
        _init_log.append("[OK] SUPABASE_URL and SUPABASE_SERVICE_KEY are set")
        # Supabase registration is handled by GitHub Actions workflow (runs outside Vercel network)
        _init_log.append("[INFO] Supabase cloud discovery: registration via GitHub Actions (external)")
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

    from django.contrib.auth.models import User
    from scanner_api.views import ensure_default_admin_user, ensure_admin_client, build_dynamic_admin_server_url

    admin_user = ensure_default_admin_user()
    _init_log.append(f"[OK] Default admin user ensured (username={admin_user.username}, password=admin123)")

    # Auto-create admin profile with company for every superuser
    from scanner_api.models import AdministratorProfile, Company
    from django.utils.text import slugify as _slugify
    for su in User.objects.filter(is_superuser=True):
        profile, _ = AdministratorProfile.objects.get_or_create(user=su)
        if not profile.company:
            _slug = _slugify(su.username) or su.username.lower().replace(" ", "-")
            company, _ = Company.objects.get_or_create(name=su.username, defaults={"slug": _slug})
            profile.company = company
            profile.save(update_fields=["company"])
    _init_log.append("[OK] Admin profiles with company ensured")

    # Ensure the admin panel's own client record exists so the admin
    # machine appears automatically on the dashboard. get_admin_client_key()
    # persists the key in Settings, so it stays stable across Vercel cold
    # starts and never floods the DB with junk ADMIN-* rows.
    try:
        admin_key = ensure_admin_client()
        _init_log.append(f"[OK] Admin client ensured: {admin_key}")
    except Exception as e:
        _init_log.append(f"[WARN] Admin client setup failed: {e}")

    from scanner_api.models import Setting
    import secrets
    vercel_url = os.getenv("VERCEL_URL", "").strip()
    if vercel_url:
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(username="admin").first()
        company = None
        if admin_user:
            profile = AdministratorProfile.objects.filter(user=admin_user).select_related("company").first()
            if profile and profile.company:
                company = profile.company
            elif admin_user.username:
                company, _ = Company.objects.get_or_create(name=admin_user.username, defaults={"slug": _slugify(admin_user.username) or admin_user.username.lower().replace(" ", "-")})
        server_url = build_dynamic_admin_server_url(f"https://{vercel_url}", getattr(admin_user, "username", "admin"), company)
        Setting.set("admin_server_url", server_url)
        _init_log.append(f"[OK] Admin connect URL set: {server_url}")
        # Register this live deployment into the Supabase cloud registry so
        # client discovery always resolves to the currently running admin.
        # This keeps the client's admin URL dynamic: every Vercel cold start
        # re-registers the current deployment, overriding stale LAN dev IPs
        # that a local admin server may have written earlier.
        try:
            from scanner_api.supabase_client import register_server_in_registry
            register_server_in_registry(vercel_url, 443, "https")
            _init_log.append(f"[OK] Cloud discovery registered: https://{vercel_url}")
        except Exception as e:
            _init_log.append(f"[WARN] Cloud discovery registration failed: {e}")
    else:
        # Empty/missing VERCEL_URL previously fell back to a dead hardcoded
        # domain and overwrote a good setting. Keep the existing value instead.
        _init_log.append("[WARN] VERCEL_URL empty → keeping existing admin_server_url setting")

    # Auto-approve is DISABLED by default. All clients require explicit admin approval.
    Setting.set("auto_approve", "false")
    _init_log.append("[OK] Auto-approve is OFF (clients require admin approval)")

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
        lines = list(_init_log)
        try:
            from django.conf import settings
            db = getattr(settings, "DATABASES", {}).get("default", {})
            lines.append(f"DB: host={db.get('HOST', '')} port={db.get('PORT', '')} conn_max_age={db.get('CONN_MAX_AGE', '')}")
            diag = getattr(settings, "DB_BOOT_DIAG", {})
            if diag:
                lines.append(f"DB_BOOT_DIAG: {diag}")
        except Exception as e:
            lines.append(f"DB: (unavailable) {e}")
        body = "\n".join(lines).encode() if lines else b"OK (no log)"
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

    # Reset endpoint: visit /__reset?token=SECRET to wipe all data and start fresh
    if path.startswith("/__reset"):
        import json as _json
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(path)
        params = parse_qs(parsed.query)
        token = params.get("token", [""])[0]
        secret = os.getenv("RESET_TOKEN", "scanner-reset-2024")
        if token != secret:
            start_response("403 Forbidden", [("Content-Type", "application/json")])
            return [b'{"error": "Invalid reset token"}']
        if _handler is None:
            start_response("503 Service Unavailable", [("Content-Type", "application/json")])
            return [b'{"error": "App not ready"}']
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # Delete all data from all tables
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                tables = [row[0] for row in cursor.fetchall()]
                for table in tables:
                    cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE')
            # Re-create admin user
            from django.contrib.auth.models import User
            from scanner_api.views import ensure_default_admin_user, build_dynamic_admin_server_url
            admin_user = ensure_default_admin_user()
            # Re-create admin profile
            from scanner_api.models import AdministratorProfile, Company
            from django.utils.text import slugify as _slugify
            su = User.objects.filter(is_superuser=True).first()
            if su:
                profile, _ = AdministratorProfile.objects.get_or_create(user=su)
                if not profile.company:
                    _slug = _slugify(su.username) or "admin"
                    company, _ = Company.objects.get_or_create(name=su.username, defaults={"slug": _slug})
                    profile.company = company
                    profile.save(update_fields=["company"])
            # Re-set settings
            import secrets as _secrets
            from scanner_api.models import Setting as _Setting
            _Setting.set("auto_approve", "false")
            _Setting.set("admin_connection_token", _secrets.token_hex(16))
            vercel_url = os.getenv("VERCEL_URL", "").strip()
            if vercel_url:
                profile = AdministratorProfile.objects.filter(user=admin_user).select_related("company").first()
                company = profile.company if profile and profile.company else Company.objects.filter(name=admin_user.username).first()
                _Setting.set("admin_server_url", build_dynamic_admin_server_url(f"https://{vercel_url}", admin_user.username, company))
            result = {"status": "ok", "message": "Database reset complete. All users, clients, and data deleted. Fresh admin user created (admin/admin123)."}
            body = _json.dumps(result, indent=2).encode()
            start_response("200 OK", [("Content-Type", "application/json")])
            return [body]
        except Exception as e:
            result = {"status": "error", "message": str(e)}
            body = _json.dumps(result, indent=2).encode()
            start_response("500 Internal Server Error", [("Content-Type", "application/json")])
            return [body]

    if _handler is None:
        msg = (_init_error or "App is still initializing, please retry in a moment")[:1000]
        start_response("503 Service Unavailable", [("Content-Type", "text/plain")])
        return [msg.encode()]

    return _handler(environ, start_response)
