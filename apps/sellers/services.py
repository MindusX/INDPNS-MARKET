from django.db import transaction

from apps.core.utils import unique_slug

from .models import SellerPlan, Shop


@transaction.atomic
def create_shop(user, data):
    plan = SellerPlan.objects.filter(code="starter").first() or SellerPlan.objects.order_by("price_monthly").first()
    if plan is None:
        raise RuntimeError("No seller plan configured. Run: python manage.py seed_initial")
    shop = Shop.objects.create(
        user=user, plan=plan, slug=unique_slug(Shop, data["name"]),
        name=data["name"], description=data.get("description", ""),
        country=data.get("country", ""), website=data.get("website", ""),
    )
    if user.role == "buyer":
        user.role = "seller"
        user.save(update_fields=["role"])
    return shop


def commission_rate_for(shop):
    return shop.plan.commission_rate
