import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-change-me-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")
ALLOWED_HOSTS_RAW = os.getenv("DJANGO_ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = ["*"] if ALLOWED_HOSTS_RAW.strip() == "*" else ALLOWED_HOSTS_RAW.split(",")

IS_VERCEL = os.getenv("VERCEL", "0") == "1"

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
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    f"{_API}.middleware.SessionTimeoutMiddleware",
    f"{_API}.middleware.SecurityHeadersMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
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

DATABASE_URL = os.getenv("DATABASE_URL", "")
if IS_VERCEL:
    _vdb = os.path.join("/tmp", "vercel.db")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _vdb,
        }
    }
elif DATABASE_URL:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", ""),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", ""),
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(os.environ.get("SCANNER_DATA_DIR", str(BASE_DIR / "data")), "scanner.db"),
        }
    }

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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if IS_VERCEL:
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
else:
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

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
