from decimal import ROUND_HALF_UP, Decimal

from django.utils.text import slugify

import uuid

CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def client_ip(request):
    # Render place le client réel en premier dans X-Forwarded-For
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def unique_slug(model, text, field="slug", max_len=60):
    base = slugify(text)[: max_len - 7] or "item"
    slug = base
    while model.objects.filter(**{field: slug}).exists():
        slug = f"{base}-{uuid.uuid4().hex[:6]}"
    return slug
