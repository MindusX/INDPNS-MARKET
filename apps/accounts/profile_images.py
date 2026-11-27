"""Enregistrement / suppression des images de profil en base (avatar, couverture) — équivalent des fonctions upload de Mindus."""
import time

from django.db import transaction

from .images import MIME
from .models import ProfileImage, User


def _next_version(old):
    return max(int(time.time() * 1000), (old or 0) + 1)         # strictement croissant : l'URL ?v= change toujours


def store_image(user, kind, data):
    """Enregistre les octets, incrémente la version (nouvelle URL) et, pour la couverture, recentre le cadrage."""
    assert kind in ("avatar", "cover")
    with transaction.atomic():
        row, _ = ProfileImage.objects.select_for_update().get_or_create(user=user)
        setattr(row, f"{kind}_data", data)
        setattr(row, f"{kind}_mime", MIME)
        row.save()
        version = _next_version(getattr(user, f"{kind}_version"))
        fields = {f"{kind}_version": version}
        if kind == "cover":
            fields["cover_position_y"] = 50
        User.objects.filter(pk=user.pk).update(**fields)
    for k, v in fields.items():
        setattr(user, k, v)
    return version


def remove_image(user, kind):
    assert kind in ("avatar", "cover")
    with transaction.atomic():
        ProfileImage.objects.filter(user=user).update(**{f"{kind}_data": None, f"{kind}_mime": ""})
        fields = {f"{kind}_version": 0}
        if kind == "cover":
            fields["cover_position_y"] = 50
        User.objects.filter(pk=user.pk).update(**fields)
    for k, v in fields.items():
        setattr(user, k, v)
