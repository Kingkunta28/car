import tempfile
from pathlib import Path

from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK, STORAGES

DEBUG = False
PAYMENT_GATEWAYS_ENABLED = ["pesapal"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
OWNER_NOTIFICATION_EMAIL = "owner@rafiki.test"
FRONTEND_URL = "https://rafiki.test"

_TMP = Path(tempfile.mkdtemp(prefix="rafiki-test-"))
MEDIA_ROOT = _TMP / "media"
PRIVATE_MEDIA_ROOT = _TMP / "private"
STORAGES = {
    **STORAGES,
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": MEDIA_ROOT}},
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": PRIVATE_MEDIA_ROOT, "base_url": None},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Throttling is covered by dedicated tests; keep the rest deterministic.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {
    k: "10000/min" for k in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
}}
PESAPAL_CONSUMER_KEY = "test-key"
PESAPAL_CONSUMER_SECRET = "test-secret"
PESAPAL_IPN_ID = "00000000-0000-0000-0000-000000000000"
