"""Traitement sécurisé des images de profil — même méthode que Mindus Forge.

  - avatar  : recadré en CARRÉ, 800 × 800 px maximum ;
  - couverture : proportions conservées, 2400 px de large maximum (le cadrage vertical se règle ensuite avec cover_position_y) ;
  - sortie toujours en JPEG progressif (qualité 88), transparence aplatie sur fond blanc, métadonnées (EXIF/GPS) supprimées.

Sécurité : on vérifie que c'est une vraie image (pas seulement l'extension), on borne taille et dimensions avant décodage
(anti « bombe de décompression ») et aucun nom de fichier fourni par l'utilisateur n'est conservé."""
import io

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}      # GIF : première image uniquement
MAX_PIXELS = 40_000_000                                # ~ 40 mégapixels en entrée
MAX_BYTES = {"avatar": 8 * 1024 * 1024, "cover": 12 * 1024 * 1024}
AVATAR_SIZE = 800
COVER_MAX_WIDTH = 2400
COVER_MAX_HEIGHT = 4800
MIME = "image/jpeg"


def process_profile_image(upload, kind):
    """Valide puis transforme un fichier téléversé. Retourne les octets JPEG prêts à être stockés en base."""
    if getattr(upload, "size", 0) > MAX_BYTES[kind]:
        raise ValidationError(_("Image too large (max %(mb)s MB).") % {"mb": MAX_BYTES[kind] // (1024 * 1024)}, code="too_large")
    try:
        upload.seek(0)
        raw = upload.read()
        img = Image.open(io.BytesIO(raw))
        fmt, (w, h) = img.format, img.size
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ValidationError(_("This file is not a valid image."), code="invalid_image")
    if not raw:
        raise ValidationError(_("This file is not a valid image."), code="invalid_image")
    if fmt not in ALLOWED_FORMATS:
        raise ValidationError(_("Images must be JPG, PNG, WebP or GIF."), code="bad_format")
    if w < 1 or h < 1 or w * h > MAX_PIXELS:
        raise ValidationError(_("This image is too large. Please use one under 40 megapixels."), code="too_many_pixels")

    try:
        img.seek(0)                                  # GIF animé : première image
        img.load()                                   # décodage complet : détecte les fichiers tronqués / corrompus
        img = ImageOps.exif_transpose(img)           # applique l'orientation ; les métadonnées sont ensuite abandonnées
    except (OSError, ValueError, SyntaxError, EOFError, Image.DecompressionBombError):
        raise ValidationError(_("This image is corrupted or cannot be read."), code="corrupt_image")

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))       # aplatissement sur fond blanc (JPEG sans alpha)
        flat.paste(rgba, mask=rgba.split()[-1])
        img = flat
    else:
        img = img.convert("RGB")

    if kind == "avatar":
        side = min(img.size)
        img = ImageOps.fit(img, (min(side, AVATAR_SIZE),) * 2, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    else:
        img.thumbnail((COVER_MAX_WIDTH, COVER_MAX_HEIGHT), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88, optimize=True, progressive=True)     # aucun exif/icc : métadonnées supprimées
    return out.getvalue()
