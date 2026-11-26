"""Règles du profil public : identifiant (username), liens sociaux, mots réservés.
Centralisé ici pour que le modèle, le formulaire et les tests partagent exactement les mêmes règles."""
import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

USERNAME_MIN, USERNAME_MAX = 3, 30
# minuscules, chiffres, « _ » et « - » ; commence et finit par un caractère alphanumérique
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,28}[a-z0-9]$")

# Noms interdits : usurpation d'identité (équipe, rôles) et mots techniques.
RESERVED_USERNAMES = frozenset({
    "admin", "administrator", "root", "system", "staff", "support", "moderator", "mod", "security", "official",
    "indpns", "indpns-market", "market", "marketplace", "team", "help", "contact", "billing", "payments",
    "api", "www", "mail", "email", "ftp", "static", "media", "files", "dashboard", "accounts", "account",
    "login", "logout", "register", "signup", "settings", "profile", "profiles", "user", "users", "u", "me",
    "shop", "shops", "seller", "sellers", "buyer", "store", "null", "none", "undefined", "anonymous",
})

GITHUB_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
TWITTER_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")
LINKEDIN_RE = re.compile(r"^[A-Za-z0-9_%-]{3,100}$")


def normalize_username(value):
    return (value or "").strip().lstrip("@").lower()


def validate_username(value):
    """Valide un identifiant déjà normalisé (modèle + formulaire)."""
    if value is None or value == "":
        return
    if not USERNAME_RE.match(value):
        raise ValidationError(
            _("Use %(min)s–%(max)s characters: lowercase letters, numbers, hyphens or underscores. Start and end with a letter or number."),
            params={"min": USERNAME_MIN, "max": USERNAME_MAX}, code="invalid_username")
    if value in RESERVED_USERNAMES:
        raise ValidationError(_("This username is reserved. Please choose another one."), code="reserved_username")


def clean_handle(value, hosts=()):
    """Accepte « @pseudo », « pseudo » ou une URL complète du réseau, et renvoie uniquement l'identifiant."""
    v = (value or "").strip()
    if not v:
        return ""
    if "/" in v or "." in v:
        parsed = urlparse(v if "//" in v else "//" + v)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if hosts and host not in hosts:
            raise ValidationError(_("Enter your username or the full URL of your profile."), code="bad_host")
        parts = [p for p in parsed.path.split("/") if p]
        if parts and parts[0] in ("in", "company", "pub", "u") and len(parts) > 1:
            parts = parts[1:]
        v = parts[0] if parts else ""
    return v.lstrip("@").strip()
