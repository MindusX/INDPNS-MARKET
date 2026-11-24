from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import ENVIRONMENT as _E, SECRET_KEY as _SK, env_bool, env_int

ENVIRONMENT = "production"
DEBUG = env_bool("DEBUG", False)
if not _SK:
    raise ImproperlyConfigured("SECRET_KEY est obligatoire en production.")
if DEBUG:
    raise ImproperlyConfigured("DEBUG doit être désactivé en production.")

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # Render termine le TLS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]   # le health check Render passe en HTTP interne
