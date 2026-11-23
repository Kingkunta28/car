from .base import *  # noqa: F401,F403
from .base import STORAGES, env
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

# Render can assign or change the generated service hostname. Trust the
# hostname Render injects at runtime; custom domains remain configured through
# DJANGO_ALLOWED_HOSTS.
_render_hostname = env("RENDER_EXTERNAL_HOSTNAME", default="").strip()
if _render_hostname and _render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_hostname)

from .base import DATABASES  # noqa: E402

if not DATABASES["default"]["ENGINE"].endswith("postgresql"):
    raise RuntimeError("Production requires PostgreSQL (set DATABASE_URL=postgres://...).")

# Neon requires TLS. Keep this explicit even if the URL omits sslmode.
DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"

# HTTPS / cookies
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/$"]
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# S3-compatible storage is optional. If disabled, uploads use the local
# filesystem; on Render's free service those files are ephemeral.
_use_s3 = env.bool("USE_S3", default=False)
SERVE_LOCAL_MEDIA = not _use_s3
# Render's local filesystem is ephemeral. Never accept passport/licence
# uploads for production bookings unless the private durable storage bucket is
# configured.
PRIVATE_DOCUMENTS_DURABLE = _use_s3

if _use_s3:
    _access_key = env("AWS_ACCESS_KEY_ID", default="").strip()
    _secret_key = env("AWS_SECRET_ACCESS_KEY", default="").strip()
    _public_bucket = env(
        "AWS_PUBLIC_BUCKET_NAME",
        default=env("AWS_STORAGE_BUCKET_NAME", default=""),
    ).strip()
    _private_bucket = env("AWS_PRIVATE_BUCKET_NAME", default="").strip()
    # Neon Object Storage provides the standard AWS_* variable names. Retain
    # the older AWS_S3_* names for other S3-compatible providers.
    _region = env("AWS_S3_REGION_NAME", default=env("AWS_REGION", default="")).strip()
    _endpoint = env(
        "AWS_S3_ENDPOINT_URL",
        default=env("AWS_ENDPOINT_URL_S3", default=""),
    ).strip() or None
    _addressing_style = env(
        "AWS_S3_ADDRESSING_STYLE",
        default="path" if _endpoint else "",
    ).strip() or None

    _missing = []
    if not _access_key:
        _missing.append("AWS_ACCESS_KEY_ID")
    if not _secret_key:
        _missing.append("AWS_SECRET_ACCESS_KEY")
    if not _public_bucket:
        _missing.append("AWS_PUBLIC_BUCKET_NAME (or AWS_STORAGE_BUCKET_NAME)")
    if not _private_bucket:
        _missing.append("AWS_PRIVATE_BUCKET_NAME")
    if not _region:
        _missing.append("AWS_S3_REGION_NAME (or AWS_REGION)")
    if _region.lower() == "auto" and not _endpoint:
        _missing.append("AWS_ENDPOINT_URL_S3 (required with region 'auto' for S3-compatible storage)")
    if _missing:
        raise ImproperlyConfigured(
            "USE_S3=True requires these Render environment variables: " + ", ".join(_missing)
        )

    _s3_common = {
        "access_key": _access_key,
        "secret_key": _secret_key,
        "endpoint_url": _endpoint,
        "region_name": _region,
        "file_overwrite": False,
    }
    if _addressing_style:
        _s3_common["addressing_style"] = _addressing_style
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": _public_bucket,
            "custom_domain": env("AWS_PUBLIC_CUSTOM_DOMAIN", default=None),
            "querystring_auth": False,
        },
    }
    STORAGES["private"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": _private_bucket,
            "querystring_auth": True,
            "querystring_expire": 60,
        },
    }

# Error monitoring
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
                    send_default_pii=False, environment=env("SENTRY_ENVIRONMENT", default="production"))
