from django.conf import settings

from apps.payments.registry import payments_enabled


def site(request):
    from apps.catalog.models import Category
    from django.core.cache import cache
    cats = cache.get("nav_categories")
    if cats is None:
        cats = list(Category.objects.filter(parent__isnull=True, is_active=True).order_by("order", "name")[:12])
        cache.set("nav_categories", cats, 300)
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_URL": settings.SITE_URL,
        "PAYMENTS_ENABLED": payments_enabled(),
        "NAV_CATEGORIES": cats,
        "DEFAULT_CURRENCY": settings.DEFAULT_CURRENCY,
        "GOOGLE_OAUTH_ENABLED": bool(settings.GOOGLE_CLIENT_ID),
        "GITHUB_OAUTH_ENABLED": bool(settings.GITHUB_CLIENT_ID),
    }
