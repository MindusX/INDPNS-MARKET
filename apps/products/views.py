from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.catalog.models import Category, Technology
from apps.core.ratelimit import ratelimit
from apps.licenses.models import License, LicenseType, ProductLicensePrice
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review

from .forms import ReportForm
from .models import Favorite, Product

SORTS = {
    "new": ["-published_at"],
    "popular": ["-sales_count", "-published_at"],
    "rating": [F("avg_rating").desc(nulls_last=True), "-review_count"],
    "price_asc": ["base_price", "-published_at"],
    "price_desc": ["-base_price", "-published_at"],
}


def _dec(v):
    try:
        return Decimal(v)
    except (InvalidOperation, TypeError):
        return None


def product_list(request, preset=None, category_slug=None):
    params = request.GET.copy()
    title = _("Explore")
    if preset == "new":
        params.setdefault("sort", "new"); title = _("New releases")
    elif preset == "popular":
        params.setdefault("sort", "popular"); title = _("Popular")
    elif preset == "top-rated":
        params.setdefault("sort", "rating"); title = _("Top rated")
    elif preset == "free":
        params["price"] = "free"; title = _("Free products")
    elif preset == "premium":
        params["price"] = "paid"; title = _("Premium products")

    qs = Product.objects.public().with_stats().select_related("shop", "category")
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        qs = qs.filter(category_id__in=category.descendant_ids())
        title = category.name
    elif params.get("category"):
        c = Category.objects.filter(slug=params["category"]).first()
        if c:
            category = c
            qs = qs.filter(category_id__in=c.descendant_ids())

    q = (params.get("q") or "").strip()[:100]
    if q:
        tech_ids = Product.objects.filter(technologies__name__icontains=q).values("pk")
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(description__icontains=q) | Q(pk__in=tech_ids))
    techs = params.getlist("tech")
    if techs:
        qs = qs.filter(pk__in=Product.objects.filter(technologies__slug__in=techs).values("pk"))
    if params.get("compat"):
        qs = qs.filter(compatibility__icontains=params["compat"][:60])
    pmin, pmax = _dec(params.get("min")), _dec(params.get("max"))
    if pmin is not None:
        qs = qs.filter(base_price__gte=pmin)
    if pmax is not None:
        qs = qs.filter(base_price__lte=pmax)
    if params.get("price") == "free":
        qs = qs.filter(base_price=0)
    elif params.get("price") == "paid":
        qs = qs.filter(base_price__gt=0)
    if params.get("license"):
        ids = ProductLicensePrice.objects.filter(license_type__code=params["license"]).values("product_id")
        qs = qs.filter(pk__in=ids)
    rmin = _dec(params.get("rating"))
    if rmin is not None:
        qs = qs.filter(avg_rating__gte=rmin)
    if params.get("since") in ("7", "30", "365"):
        qs = qs.filter(published_at__gte=timezone.now() - timedelta(days=int(params["since"])))
    sort = params.get("sort") if params.get("sort") in SORTS else "new"
    qs = qs.order_by(*SORTS[sort])

    page = Paginator(qs, 24).get_page(params.get("page"))
    fav_ids = set()
    if request.user.is_authenticated:
        fav_ids = set(Favorite.objects.filter(user=request.user, product__in=[p.pk for p in page]).values_list("product_id", flat=True))
    return render(request, "public/explore.html", {
        "page": page, "title": title, "q": q, "category": category, "sort": sort, "params": params,
        "categories": Category.objects.filter(parent__isnull=True, is_active=True).prefetch_related("children"),
        "technologies": Technology.objects.all()[:40], "selected_techs": techs, "license_types": LicenseType.objects.all(),
        "fav_ids": fav_ids, "total": page.paginator.count,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("shop", "category").prefetch_related("technologies", "images", "versions"), slug=slug)
    u = request.user
    if product.status != "approved":
        is_owner = u.is_authenticated and hasattr(u, "shop") and product.shop_id == u.shop.pk
        if not (is_owner or (u.is_authenticated and u.has_role_at_least("moderator"))):
            raise Http404
    stats = Product.objects.with_stats().filter(pk=product.pk).values("avg_rating", "review_count", "sales_count").first()
    prices = list(ProductLicensePrice.objects.filter(product=product).select_related("license_type"))
    reviews = Review.objects.filter(product=product, is_visible=True).select_related("user")[:20]
    similar = (Product.objects.public().with_stats().filter(category=product.category).exclude(pk=product.pk)
               .select_related("shop")[:4]) if product.category_id else []
    owned = None
    is_fav = False
    review_form = None
    if u.is_authenticated:
        owned = License.objects.filter(buyer=u, product=product, revoked_at__isnull=True).first()
        is_fav = Favorite.objects.filter(user=u, product=product).exists()
        if owned and not Review.objects.filter(user=u, product=product).exists():
            review_form = ReviewForm()
    return render(request, "public/product_detail.html", {
        "product": product, "stats": stats, "prices": prices, "reviews": reviews, "similar": similar,
        "owned": owned, "is_fav": is_fav, "review_form": review_form, "report_form": ReportForm(),
        "versions": [v for v in product.versions.all() if v.is_safe],
    })


@login_required
@require_POST
def toggle_favorite(request, slug):
    product = get_object_or_404(Product.objects.public(), slug=slug)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if not created:
        fav.delete()
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"favorite": created})
    return redirect(request.POST.get("next") or product.get_absolute_url())


@login_required
@require_POST
@ratelimit("report", limit=10, window=3600)
def report_product(request, slug):
    product = get_object_or_404(Product.objects.public(), slug=slug)
    form = ReportForm(request.POST)
    if form.is_valid():
        r = form.save(commit=False)
        r.product, r.reporter = product, request.user
        r.save()
        messages.success(request, _("Thank you. Our team will review your report."))
    else:
        messages.error(request, _("Could not send the report. Please check the form."))
    return redirect(product.get_absolute_url())
