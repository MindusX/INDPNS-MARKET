from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from apps.products.models import Product

from .models import SellerPlan, Shop


def pricing(request):
    plans = SellerPlan.objects.filter(is_active=True)
    return render(request, "public/pricing.html", {
        "plans": plans, "subscriptions_enabled": settings.SUBSCRIPTIONS_ENABLED and bool(settings.PAYMENT_PROVIDER),
    })


def shop_list(request):
    qs = (Shop.objects.filter(is_active=True)
          .annotate(n=Count("products", filter=Q(products__status="approved")))
          .filter(n__gt=0).order_by("-n", "name"))
    page = Paginator(qs, 24).get_page(request.GET.get("page"))
    return render(request, "public/shops.html", {"page": page})


def shop_detail(request, slug):
    shop = get_object_or_404(Shop, slug=slug, is_active=True)
    products = Product.objects.public().filter(shop=shop).with_stats()
    page = Paginator(products, 24).get_page(request.GET.get("page"))
    return render(request, "public/shop_detail.html", {"shop": shop, "page": page})
