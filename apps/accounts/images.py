"""Traitement sécurisé des images de profil (avatar, couverture).

Pourquoi ré-encoder ? Une image publique téléversée par un utilisateur ne doit jamais être servie telle quelle :
  - on vérifie que c'est vraiment une image (pas seulement l'extension) et on borne les dimensions (anti « bombe de décompression ») ;
  - on supprime les métadonnées (EXIF, GPS de la photo…) : confidentialité de l'utilisateur ;
  - on recadre et on redimensionne : poids réduit, rendu identique partout ;
  - on enregistre en WebP sous un nom aléatoire : aucun nom de fichier fourni par l'utilisateur n'est conservé.
"""
import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000          # ~ 40 mégapixels en entrée (au-delà : refus avant décodage)

# kind -> (taille finale, taille minimale acceptée, qualité WebP)
SPECS = {
    "avatar": {"size": (512, 512), "min": (128, 128), "quality": 86},
    "cover": {"size": (1500, 500), "min": (800, 266), "quality": 82},
}


def process_profile_image(upload, kind):
    """Valide puis transforme un fichier téléversé. Retourne un ContentFile WebP prêt à être stocké."""
    spec = SPECS[kind]
    try:
        upload.seek(0)
        raw = upload.read()
        img = Image.open(io.BytesIO(raw))
        fmt, (w, h) = img.format, img.size
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ValidationError(_("This file is not a valid image."), code="invalid_image")

    if fmt not in ALLOWED_FORMATS:
        raise ValidationError(_("Images must be JPG, PNG or WebP."), code="bad_format")
    if w * h > MAX_PIXELS:
        raise ValidationError(_("This image is too large. Please use one under 40 megapixels."), code="too_many_pixels")
    if w < spec["min"][0] or h < spec["min"][1]:
        raise ValidationError(
            _("Image too small: minimum %(w)s × %(h)s pixels."),
            params={"w": spec["min"][0], "h": spec["min"][1]}, code="too_small")

    try:
        img.load()                                   # décodage complet : détecte les fichiers tronqués / corrompus
        img = ImageOps.exif_transpose(img)           # applique l'orientation, puis les métadonnées sont abandonnées
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise ValidationError(_("This image is corrupted or cannot be read."), code="corrupt_image")

    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")
    img = ImageOps.fit(img, spec["size"], method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    out = io.BytesIO()
    img.save(out, format="WEBP", quality=spec["quality"], method=4)      # aucun paramètre exif/icc : métadonnées supprimées
    return ContentFile(out.getvalue(), name=f"{uuid.uuid4().hex}.webp")
