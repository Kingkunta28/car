"""
Base settings shared by every environment.

All secrets and environment-specific values are read from environment
variables (or a local, uncommitted .env file). See .env.example.
"""
from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "django_filters",
    "corsheaders",
    # Local
    "apps.core",
    "apps.accounts",
    "apps.customers",
    "apps.vehicles",
    "apps.bookings",
    "apps.invoices",
    "apps.payments",
    "apps.notifications",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "accounts.AdminUser"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --------------------------------------------------------------------------
# Database — PostgreSQL is required (exclusion constraints, range types).
# --------------------------------------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    # SQLite is for local development only. Production must use PostgreSQL,
    # which adds the database-level double-booking EXCLUSION constraint.
    name = Path(DATABASES["default"]["NAME"])
    DATABASES["default"]["NAME"] = str(name if name.is_absolute() else BASE_DIR / name)
    DATABASES["default"]["OPTIONS"] = {"timeout": 20, "transaction_mode": "IMMEDIATE"}
else:
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# --------------------------------------------------------------------------
# Passwords & auth
# --------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 60 * 8)  # 8 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:5173"])

# --------------------------------------------------------------------------
# I18N
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Dar_es_Salaam"  # Zanzibar (EAT, UTC+3)
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static, public media and PRIVATE media
# --------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # public: vehicle photos, logo
PRIVATE_MEDIA_ROOT = Path(env("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private_media")))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Passports, licences, payment proofs, invoices and receipts.
    # Never served by a URL: only streamed through permission-checked views.
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": PRIVATE_MEDIA_ROOT, "base_url": None},
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=8)
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    # Secure by default: every view must explicitly opt in to public access.
    "DEFAULT_PERMISSION_CLASSES": ["apps.accounts.permissions.DashboardPermission"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="600/hour"),
        "user": env("THROTTLE_USER", default="5000/hour"),
        "booking_create": env("THROTTLE_BOOKING_CREATE", default="10/hour"),
        "quote": env("THROTTLE_QUOTE", default="120/min"),
        "booking_access": env("THROTTLE_BOOKING_ACCESS", default="60/hour"),
        "payment": env("THROTTLE_PAYMENT", default="20/hour"),
        "contact": env("THROTTLE_CONTACT", default="5/hour"),
        "login": env("THROTTLE_LOGIN", default="10/hour"),
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "COERCE_DECIMAL_TO_STRING": True,
    "DATETIME_FORMAT": "iso-8601",
}

# --------------------------------------------------------------------------
# CORS (the frontend normally proxies /api to the backend, so same-origin)
# --------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept", "content-type", "x-csrftoken", "x-requested-with",
    "x-booking-token", "x-booking-reference",
]
CORS_EXPOSE_HEADERS = ["content-disposition"]

# --------------------------------------------------------------------------
# Cache (Redis in production; used by throttling and gateway tokens)
# --------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --------------------------------------------------------------------------
# Celery
# --------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL or "memory://")
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "release-expired-holds": {
        "task": "apps.bookings.tasks.release_expired_holds",
        "schedule": timedelta(minutes=10),
    },
    "process-notification-queue": {
        "task": "apps.notifications.tasks.process_notification_queue",
        "schedule": timedelta(minutes=5),
    },
    "purge-expired-documents": {
        "task": "apps.bookings.tasks.purge_expired_documents",
        "schedule": crontab(hour=3, minute=15),
    },
    "reconcile-online-payments": {
        "task": "apps.payments.tasks.reconcile_pending_online_payments",
        "schedule": timedelta(minutes=15),
    },
}

# --------------------------------------------------------------------------
# Email (SMTP — works with Resend, Brevo, Postmark, Mailgun SMTP relays)
# --------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Rafiki Car Hire <bookings@localhost>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
NOTIFICATION_MAX_ATTEMPTS = env.int("NOTIFICATION_MAX_ATTEMPTS", default=6)

# --------------------------------------------------------------------------
# Business configuration
# --------------------------------------------------------------------------
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173").rstrip("/")
BACKEND_URL = env("BACKEND_URL", default="http://localhost:8000").rstrip("/")
OWNER_NOTIFICATION_EMAIL = env("OWNER_NOTIFICATION_EMAIL", default="")
BOOKING_HOLD_HOURS = env.int("BOOKING_HOLD_HOURS", default=24)
BOOKING_TURNAROUND_HOURS = env.int("BOOKING_TURNAROUND_HOURS", default=2)
BOOKING_MIN_LEAD_HOURS = env.int("BOOKING_MIN_LEAD_HOURS", default=3)
BOOKING_MAX_RENTAL_DAYS = env.int("BOOKING_MAX_RENTAL_DAYS", default=90)
BOOKING_MAX_ADVANCE_DAYS = env.int("BOOKING_MAX_ADVANCE_DAYS", default=540)
BOOKING_ACCESS_TOKEN_DAYS = env.int("BOOKING_ACCESS_TOKEN_DAYS", default=120)
DOCUMENT_RETENTION_DAYS = env.int("DOCUMENT_RETENTION_DAYS", default=30)
DEFAULT_ARRIVAL_AIRPORT = "Abeid Amani Karume International Airport, Zanzibar"
CURRENCY = "USD"

# --------------------------------------------------------------------------
# Payment gateways (credentials only ever from the environment)
# --------------------------------------------------------------------------
PAYMENT_GATEWAYS_ENABLED = env.list("PAYMENT_GATEWAYS_ENABLED", default=["pesapal"])
PESAPAL_ENV = env("PESAPAL_ENV", default="sandbox")
PESAPAL_CONSUMER_KEY = env("PESAPAL_CONSUMER_KEY", default="")
PESAPAL_CONSUMER_SECRET = env("PESAPAL_CONSUMER_SECRET", default="")
PESAPAL_IPN_ID = env("PESAPAL_IPN_ID", default="")

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
DJANGO_ADMIN_URL = env("DJANGO_ADMIN_URL", default="django-admin/")
