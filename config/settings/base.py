"""Réglages communs. Aucun secret en dur : tout vient de l'environnement."""
import os
from pathlib import Path

import dj_database_url
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def env_int(name, default=0):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def env_list(name, default=""):
    return [x.strip() for x in env(name, default).split(",") if x.strip()]


ENVIRONMENT = env("ENVIRONMENT", "development")
DEBUG = env_bool("DEBUG", False)
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
SITE_URL = env("SITE_URL", "http://localhost:8000").rstrip("/")
SITE_NAME = "INDPNS Market"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.core",
    "apps.accounts",
    "apps.sellers",
    "apps.catalog",
    "apps.products",
    "apps.licenses",
    "apps.orders",
    "apps.payments",
    "apps.commissions",
    "apps.payouts",
    "apps.reviews",
    "apps.moderation",
    "apps.notifications",
    "apps.dashboard",
]

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "core:home"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.template.context_processors.i18n",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "apps.core.context_processors.site",
        "apps.notifications.context_processors.notifications",
    ]},
}]

# ---------- Base de données (Neon) ----------
_db_url = env("DATABASE_URL") or env("NEON_DATABASE_URL")
if _db_url:
    DATABASES = {"default": dj_database_url.parse(
        _db_url, conn_max_age=env_int("DB_CONN_MAX_AGE", 60),
        ssl_require=env_bool("DATABASE_SSL_REQUIRE", ENVIRONMENT == "production"))}
    # Neon pooled (host contenant « -pooler ») = PgBouncer en mode transaction.
    if "-pooler" in (DATABASES["default"].get("HOST") or "") or env_bool("DATABASE_POOLED"):
        DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
        DATABASES["default"].setdefault("OPTIONS", {})["prepare_threshold"] = None
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- Cache / Celery (Redis) ----------
REDIS_URL = env("REDIS_URL")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_ENABLED = bool(REDIS_URL) and env_bool("CELERY_ENABLED", True)
CELERY_BROKER_URL = REDIS_URL or "memory://"
CELERY_RESULT_BACKEND = REDIS_URL or None
CELERY_TASK_ALWAYS_EAGER = not CELERY_ENABLED

# ---------- Mots de passe ----------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------- i18n ----------
LANGUAGE_CODE = "en"
LANGUAGES = [("en", _("English")), ("fr", _("Français")), ("es", _("Español"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_CURRENCY = "USD"

# ---------- Statique / médias ----------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"            # visuels publics uniquement (covers, galerie)
PRIVATE_FILES_ROOT = Path(env("PRIVATE_FILES_ROOT", str(BASE_DIR / "private_files")))  # fichiers vendus, jamais servis publiquement

# S3 compatible (fichiers vendus privés + médias)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL") or None
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME") or None
AWS_QUERYSTRING_EXPIRE = env_int("DOWNLOAD_LINK_TTL", 300)
S3_ENABLED = bool(AWS_STORAGE_BUCKET_NAME and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
if S3_ENABLED:   # visuels publics (covers, galerie) sur S3 ; les fichiers vendus utilisent un stockage privé séparé
    STORAGES["default"] = {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
                           "OPTIONS": {"location": "public", "default_acl": "public-read", "querystring_auth": False}}

# ---------- Uploads ----------
MAX_PRODUCT_FILE_MB = env_int("MAX_PRODUCT_FILE_MB", 200)
MAX_IMAGE_MB = env_int("MAX_IMAGE_MB", 5)
MAX_ARCHIVE_ENTRIES = env_int("MAX_ARCHIVE_ENTRIES", 20000)
MAX_ARCHIVE_UNCOMPRESSED_MB = env_int("MAX_ARCHIVE_UNCOMPRESSED_MB", 1500)
BLOCKED_ARCHIVE_EXTENSIONS = set(env_list("BLOCKED_ARCHIVE_EXTENSIONS", ".exe,.scr,.com,.msi,.vbs,.pif,.cpl"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
ANTIVIRUS_ENABLED = env_bool("ANTIVIRUS_ENABLED", False)
ANTIVIRUS_REQUIRED = env_bool("ANTIVIRUS_REQUIRED", False)   # True = rien n'est publié sans scan « clean »
ANTIVIRUS_CLAMD_HOST = env("ANTIVIRUS_CLAMD_HOST", "127.0.0.1")
ANTIVIRUS_CLAMD_PORT = env_int("ANTIVIRUS_CLAMD_PORT", 3310)

# ---------- E-mail ----------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend" if env("EMAIL_HOST") else "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "INDPNS Market <no-reply@indpns.com>")
EMAIL_VERIFICATION_REQUIRED = env_bool("EMAIL_VERIFICATION_REQUIRED", True)

# ---------- Paiements ----------
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER").lower()      # "" = mode catalogue | "stripe" | "paypal"
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET")
PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = env("PAYPAL_CLIENT_SECRET")
PAYPAL_WEBHOOK_ID = env("PAYPAL_WEBHOOK_ID")
PAYOUT_HOLD_DAYS = env_int("PAYOUT_HOLD_DAYS", 14)
MIN_PAYOUT_AMOUNT = env("MIN_PAYOUT_AMOUNT", "20.00")
SUBSCRIPTIONS_ENABLED = env_bool("SUBSCRIPTIONS_ENABLED", False)   # facturation d'abonnements vendeurs : non implémentée

# ---------- OAuth (architecture prête, inactif sans clés) ----------
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GITHUB_CLIENT_ID = env("GITHUB_CLIENT_ID")

# ---------- DRF ----------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "240/min"},
}

# ---------- Sécurité de session ----------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
ADMIN_URL = env("ADMIN_URL", "admin/").strip("/") + "/"

LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}

SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=SENTRY_DSN, send_default_pii=False, traces_sample_rate=0.0)
    except ImportError:  # pragma: no cover
        pass
