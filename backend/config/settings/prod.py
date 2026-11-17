from .base import *  # noqa: F401,F403
from .base import STORAGES, env

DEBUG = False

from .base import DATABASES  # noqa: E402

if not DATABASES["default"]["ENGINE"].endswith("postgresql"):
    raise RuntimeError("Production requires PostgreSQL (set DATABASE_URL=postgres://...).")

# HTTPS / cookies
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/$"]
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Object storage (S3-compatible: AWS S3, Cloudflare R2, Backblaze B2, DO Spaces)
if env.bool("USE_S3", default=False):
    _s3_common = {
        "access_key": env("AWS_ACCESS_KEY_ID"),
        "secret_key": env("AWS_SECRET_ACCESS_KEY"),
        "endpoint_url": env("AWS_S3_ENDPOINT_URL", default=None),
        "region_name": env("AWS_S3_REGION_NAME", default=None),
        "file_overwrite": False,
    }
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": env("AWS_PUBLIC_BUCKET_NAME"),
            "custom_domain": env("AWS_PUBLIC_CUSTOM_DOMAIN", default=None),
            "querystring_auth": False,
        },
    }
    STORAGES["private"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": env("AWS_PRIVATE_BUCKET_NAME"),
            "default_acl": "private",
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
