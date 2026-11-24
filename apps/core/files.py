"""Validation des fichiers téléversés. Aucun fichier n'est jamais exécuté."""
import hashlib
import os
import posixpath
import zipfile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

ALLOWED_PRODUCT_EXT = {".zip", ".pdf"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def validate_product_file(f):
    name = os.path.basename(f.name or "")
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_PRODUCT_EXT:
        raise ValidationError(_("Unsupported file type. Allowed: %(ext)s"), params={"ext": ", ".join(sorted(ALLOWED_PRODUCT_EXT))})
    if f.size > settings.MAX_PRODUCT_FILE_MB * 1024 * 1024:
        raise ValidationError(_("File too large (max %(mb)s MB)."), params={"mb": settings.MAX_PRODUCT_FILE_MB})
    f.seek(0)
    head = f.read(8)
    f.seek(0)
    if ext == ".pdf" and not head.startswith(b"%PDF-"):
        raise ValidationError(_("This file is not a valid PDF."))
    if ext == ".zip":
        if not head.startswith((b"PK\x03\x04", b"PK\x05\x06")):
            raise ValidationError(_("This file is not a valid ZIP archive."))
        _inspect_zip(f)
        f.seek(0)


def _inspect_zip(f):
    try:
        with zipfile.ZipFile(f) as z:
            infos = z.infolist()
            if len(infos) > settings.MAX_ARCHIVE_ENTRIES:
                raise ValidationError(_("The archive contains too many files."))
            total = 0
            for i in infos:
                n = i.filename.replace("\\", "/")
                if n.startswith("/") or ".." in posixpath.normpath(n).split("/"):
                    raise ValidationError(_("The archive contains unsafe paths."))
                if os.path.splitext(n)[1].lower() in settings.BLOCKED_ARCHIVE_EXTENSIONS:
                    raise ValidationError(_("The archive contains a blocked file type: %(n)s"), params={"n": os.path.basename(n)})
                total += i.file_size
            if total > settings.MAX_ARCHIVE_UNCOMPRESSED_MB * 1024 * 1024:
                raise ValidationError(_("The archive is too large once extracted."))
    except zipfile.BadZipFile:
        raise ValidationError(_("The ZIP archive is corrupted."))


def validate_image_file(f):
    ext = os.path.splitext(f.name or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValidationError(_("Images must be JPG, PNG or WebP."))
    if f.size > settings.MAX_IMAGE_MB * 1024 * 1024:
        raise ValidationError(_("Image too large (max %(mb)s MB)."), params={"mb": settings.MAX_IMAGE_MB})


def sha256_of(fieldfile):
    h = hashlib.sha256()
    fieldfile.open("rb")
    try:
        for chunk in iter(lambda: fieldfile.read(1024 * 1024), b""):
            h.update(chunk)
    finally:
        fieldfile.close()
    return h.hexdigest()
