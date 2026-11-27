"""Traitement des images de pièces d'identité (KYC).

On ne stocke JAMAIS le fichier brut : on vérifie que c'est une vraie image, on borne dimensions et poids (anti « bombe de
décompression »), on exige une résolution lisible, puis on ré-encode en JPEG sans métadonnées (EXIF/GPS supprimés).
Les PDF ne sont pas acceptés (surface d'attaque inutile : une photo ou un scan en image suffit)."""
import io

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 50_000_000
MIN_SIDE = 400
MAX_SIDE = 2600
MIME = "image/jpeg"


def process_document_image(upload):
    """Valide puis ré-encode une image de document. Retourne les octets JPEG (non chiffrés : le chiffrement est fait par le service)."""
    if getattr(upload, "size", 0) > MAX_BYTES:
        raise ValidationError(_("File too large (max %(mb)s MB).") % {"mb": MAX_BYTES // (1024 * 1024)}, code="too_large")
    try:
        upload.seek(0)
        raw = upload.read()
        img = Image.open(io.BytesIO(raw))
        fmt, (w, h) = img.format, img.size
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ValidationError(_("This file is not a valid image. Upload a JPG, PNG or WebP photo."), code="invalid_image")
    if not raw or fmt not in ALLOWED_FORMATS:
        raise ValidationError(_("Upload a JPG, PNG or WebP photo (PDF files are not accepted)."), code="bad_format")
    if w * h > MAX_PIXELS:
        raise ValidationError(_("This image is too large. Please use one under 50 megapixels."), code="too_many_pixels")
    if min(w, h) < MIN_SIDE:
        raise ValidationError(_("The image is too small to be readable (minimum %(px)s px on the short side).") % {"px": MIN_SIDE}, code="too_small")
    try:
        img.load()
        img = ImageOps.exif_transpose(img)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise ValidationError(_("This image is corrupted or cannot be read."), code="corrupt_image")

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.split()[-1])
        img = flat
    else:
        img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88, optimize=True)        # sans exif/icc : métadonnées supprimées
    return out.getvalue()
