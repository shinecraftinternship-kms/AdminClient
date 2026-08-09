import os
from pathlib import Path
from dotenv import load_dotenv

from runtime import get_data_dir

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-change-me-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS_RAW = os.getenv("DJANGO_ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = ["*"] if ALLOWED_HOSTS_RAW.strip() == "*" else ALLOWED_HOSTS_RAW.split(",")

IS_VERCEL = os.getenv("VERCEL", "0") == "1"

try:
    import corsheaders.middleware as _corsheaders_middleware  # noqa: F401
    CORS_MIDDLEWARE_PATH = "corsheaders.middleware.CorsMiddleware"
except Exception:
    CORS_MIDDLEWARE_PATH = "corsheaders.middleware.CorsHeadersMiddleware"

_API = "scanner_api"
_MON = "monitoring"
_MNT = "maintenance"
_INT = "intelligence"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    _API,
    _MON,
    _MNT,
    _INT,
]

if not IS_VERCEL:
    INSTALLED_APPS.insert(0, "daphne")
    INSTALLED_APPS.insert(5, "channels")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    CORS_MIDDLEWARE_PATH,
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "scanner_api.middleware.CookieAuthMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    f"{_API}.middleware.CompanyPrefixMiddleware",
    f"{_API}.middleware.SessionTimeoutMiddleware",
    f"{_API}.middleware.SecurityHeadersMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "scanner_api.session_auth.CsrfExemptSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_PAGINATION_CLASS": None,
}

ROOT_URLCONF = "django_admin.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                f"{_API}.middleware.url_prefix_context",
            ],
        },
    },
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"

WSGI_APPLICATION = "django_admin.wsgi.application"
ASGI_APPLICATION = "django_admin.asgi.application"

if not IS_VERCEL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "CONFIG": {
                "capacity": 1000,
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "CONFIG": {
                "capacity": 1000,
            },
        },
    }

WS_HEARTBEAT_INTERVAL = 30
WS_AGENT_GROUP_PREFIX = "agent"
WS_DASHBOARD_GROUP = "dashboard"

MONITORING_HEARTBEAT_INTERVAL = 30
MONITORING_WARNING_SECONDS = 300
MONITORING_OFFLINE_SECONDS = 900
MONITORING_CRITICAL_SECONDS = 1800

SCHEDULER_CONFIG = {
    "job_defaults": {
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 300,
    },
}

JWT_SECRET = SECRET_KEY
JWT_ALGORITHM = "HS256"
JWT_ACCESS_EXPIRY_MINUTES = 60
JWT_REFRESH_EXPIRY_DAYS = 7
JWT_ISSUER = "system-scanner-pro"

DB_BOOT_DIAG = {}

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_BOOT_DIAG["raw_url"] = True if DATABASE_URL else False
if DATABASE_URL:
    from urllib.parse import urlsplit, urlunsplit
    _dbu = urlsplit(DATABASE_URL)
    DB_BOOT_DIAG["hostname"] = _dbu.hostname
    DB_BOOT_DIAG["url_port"] = _dbu.port
    DB_BOOT_DIAG["pooler_in_url"] = "pooler.supabase.com" in DATABASE_URL
    DB_BOOT_DIAG["masked_netloc"] = __import__("re").sub(r":([^@]*)@", ":****@", _dbu.netloc)
    if "pooler.supabase.com" in DATABASE_URL:
        # Supabase pooler session mode (port 5432) caps at pool_size=15
        # concurrent connections. Vercel serverless bursts easily exceed this
        # → EMAXCONNSESSION errors and 500s. Transaction mode (port 6543)
        # multiplexes up to 10k connections and is built for serverless.
        # Rewritten unconditionally (env-based Vercel detection is unreliable);
        # port 6543 works for both serverless and persistent servers.
        parts = list(urlsplit(DATABASE_URL))
        netloc = parts[1]
        userinfo, _, hostport = netloc.rpartition("@")
        if ":" in hostport:
            host, port = hostport.rsplit(":", 1)
        else:
            host, port = hostport, ""
        if not port or (port.isdigit() and int(port) != 6543):
            new_hostport = f"{host}:6543"
            parts[1] = f"{userinfo}@{new_hostport}" if userinfo else new_hostport
            DATABASE_URL = urlunsplit(parts)
    import dj_database_url
    if "sslmode=" not in DATABASE_URL:
        separator = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"
    # 0 = close after each request (required for Vercel serverless).
    # Persistent servers reuse connections to avoid repeated DNS lookups,
    # which are flaky for the Supabase pooler on IPv4-only hosts.
    conn_max_age = int(os.getenv("DB_CONN_MAX_AGE", "0" if IS_VERCEL else "10"))
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=conn_max_age,
        )
    }
    # Bulletproof override: regardless of how the URL parsed, force transaction
    # mode (6543) whenever the effective host is the Supabase pooler. Session
    # mode (5432) caps at pool_size=15 and 500s under serverless bursts.
    _eff_host = str(DATABASES["default"].get("HOST", ""))
    _eff_port = str(DATABASES["default"].get("PORT", ""))
    if _eff_host.endswith("pooler.supabase.com") and _eff_port in ("", "5432"):
        DATABASES["default"]["PORT"] = "6543"
    DB_BOOT_DIAG["final_host"] = DATABASES["default"].get("HOST")
    DB_BOOT_DIAG["final_port"] = DATABASES["default"].get("PORT")
    # Add robust options to prevent "always checking" / hanging connections on Vercel
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].update({
        "connect_timeout": 10,       # fail fast if DB unreachable (seconds)
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "sslmode": "require",
    })
elif IS_VERCEL:
    # Vercel without DATABASE_URL → warn loudly (SQLite /tmp is ephemeral!)
    import warnings
    warnings.warn(
        "DATABASE_URL is not set! Falling back to ephemeral SQLite on /tmp. "
        "Login data will be lost on every request. Set DATABASE_URL in Vercel Dashboard.",
        RuntimeWarning,
    )
    _vdb = os.path.join("/tmp", "vercel.db")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _vdb,
        }
    }
else:
    database_dir = get_data_dir(os.environ.get("SCANNER_DATA_DIR"), str(BASE_DIR / "data"))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(database_dir, "scanner.db"),
        }
    }

# ── Supabase (make keys available via Django settings) ────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Serve static files from source dirs (no collectstatic step needed on Vercel).
# Uses the staticfiles finders (STATICFILES_DIRS + each app's static/ folder).
WHITENOISE_USE_FINDERS = True

AUTHENTICATION_BACKENDS = [
    "scanner_api.auth_backend.ResilientModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]

if DATABASE_URL:
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
elif IS_VERCEL:
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
else:
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

if IS_VERCEL:
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_DOMAIN = None
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_HTTPONLY = False
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = False

SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# Save the session only when modified. With DB-backed sessions (Supabase),
# saving on every request forces a Postgres round-trip on every page load,
# which makes navigation feel slow (or time out / get "interrupted").
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {message}", "style": "{", "datefmt": "%Y-%m-%d %H:%M:%S"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "scanner_api": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "monitoring": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "channels": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "daphne": {"handlers": ["console"], "level": "INFO", "propagate": False},

    },
}
