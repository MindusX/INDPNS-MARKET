import logging
import secrets

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import ENVIRONMENT as _E, SECRET_KEY as _SK, env_bool, env_int

ENVIRONMENT = "production"
DEBUG = env_bool("DEBUG", False)
if not _SK:
    # Démarrage de secours : clé aléatoire éphémère. Les sessions et liens signés sont invalidés à chaque
    # redémarrage. Définissez SECRET_KEY dans les variables d'environnement Render dès que possible.
    SECRET_KEY = secrets.token_urlsafe(64)
    logging.getLogger(__name__).warning("SECRET_KEY is not set: using an EPHEMERAL key. Set SECRET_KEY on Render.")
if DEBUG:
    raise ImproperlyConfigured("DEBUG doit être désactivé en production.")

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # Render termine le TLS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]   # le health check Render passe en HTTP interne

# Médias publics (photos de profil, couvertures, logos, visuels produits) : sans S3, le disque de Render est éphémère
# (effacé à chaque déploiement). On les stocke donc dans la base de données, persistante.
if not S3_ENABLED:  # noqa: F405
    STORAGES["default"] = {"BACKEND": "apps.core.storage.DatabaseStorage"}  # noqa: F405

if not (BREVO_API_KEY and MAIL_FROM) and EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":  # noqa: F405
    logging.getLogger(__name__).warning("BREVO_API_KEY / MAIL_FROM are not set: e-mails are only printed to the logs. Set them on Render.")
