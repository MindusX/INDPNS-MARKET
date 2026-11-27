"""Chiffrement des données sensibles au repos (pièces d'identité KYC) — Fernet (AES-128-CBC + HMAC-SHA256).

Clés : KYC_ENCRYPTION_KEY (une ou plusieurs clés Fernet séparées par des virgules ; la première chiffre, toutes déchiffrent,
ce qui permet la rotation) ; à défaut, dérivée de SECRET_KEY. Si ni l'une ni l'autre n'est fixée dans l'environnement
(SECRET_KEY éphémère), on refuse de chiffrer : les documents deviendraient illisibles au prochain démarrage."""
import base64
import hashlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def encryption_available():
    return bool(getattr(settings, "KYC_KEY_CONFIGURED", False))


def _fernet():
    from cryptography.fernet import Fernet, MultiFernet

    keys = []
    for raw in (getattr(settings, "KYC_ENCRYPTION_KEY", "") or "").split(","):
        raw = raw.strip()
        if raw:
            try:
                keys.append(Fernet(raw.encode()))
            except (ValueError, TypeError):
                raise ImproperlyConfigured("KYC_ENCRYPTION_KEY n'est pas une clé Fernet valide (32 octets en base64 URL-safe).")
    if not keys:
        if not encryption_available():
            raise ImproperlyConfigured("Définissez KYC_ENCRYPTION_KEY (ou un SECRET_KEY fixe) pour chiffrer les documents d'identité.")
        digest = hashlib.sha256(("indpns-kyc-documents:" + settings.SECRET_KEY).encode()).digest()
        keys.append(Fernet(base64.urlsafe_b64encode(digest)))
    return MultiFernet(keys)


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt_bytes(token) -> bytes:
    return _fernet().decrypt(bytes(token))
