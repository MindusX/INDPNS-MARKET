import io
import json
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import connection
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.templatetags.static import static
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache

from apps.catalog.models import Category
from apps.products.models import Favorite, Product
from apps.sellers.models import Shop

from .forms import ContactForm
from .ratelimit import ratelimit

STATIC_PAGES = {"about", "mission", "help", "faq", "docs", "how-to-buy", "how-to-sell", "license-guide", "affiliate"}
LEGAL_PAGES = {
    "privacy": "Privacy Policy", "terms": "Terms of Service", "seller-terms": "Seller Terms", "cookies": "Cookie Policy",
    "refund": "Refund Policy", "ip": "Intellectual Property", "report": "Report Content", "retention": "Data Retention",
}


def home(request):
    base = Product.objects.public().with_stats().select_related("shop", "category")
    ctx = {
        "popular": base.filter(sales_count__gt=0).order_by("-sales_count")[:8],
        "newest": base.order_by("-published_at")[:8],
        "top_rated": base.filter(review_count__gt=0).order_by("-avg_rating", "-review_count")[:8],
        "categories": Category.objects.filter(parent__isnull=True, is_active=True)[:8],
        "recommended": [],
        "plans_url": "sellers:pricing",
    }
    if request.user.is_authenticated:
        cat_ids = list(Favorite.objects.filter(user=request.user).values_list("product__category_id", flat=True)[:20])
        if cat_ids:
            owned = request.user.licenses.values_list("product_id", flat=True)
            ctx["recommended"] = base.filter(category_id__in=cat_ids).exclude(pk__in=owned).order_by("-published_at")[:4]
    ctx["top_shops"] = [s for s in Shop.objects.filter(is_active=True).order_by("-created_at")[:50] if s.products.filter(status="approved").exists()][:6]
    return render(request, "public/home.html", ctx)


def static_page(request, page):
    if page not in STATIC_PAGES:
        raise Http404
    try:
        return render(request, f"public/pages/{page}.html", {"page_slug": page})
    except TemplateDoesNotExist:
        raise Http404


def legal_page(request, slug):
    if slug not in LEGAL_PAGES:
        raise Http404
    return render(request, "public/legal/page.html", {"slug": slug, "title": LEGAL_PAGES[slug], "legal_pages": LEGAL_PAGES,
                                                       "body_template": f"public/legal/{slug}.html"})


@ratelimit("contact", limit=5, window=3600)
def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Message sent. We will get back to you by email."))
        return redirect("core:contact")
    return render(request, "public/pages/contact.html", {"form": form})


def download_page(request):
    qr = cache.get("qr_download_svg")
    if qr is None:
        try:
            import qrcode
            import qrcode.image.svg
            img = qrcode.make(settings.SITE_URL + "/download/", image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
            buf = io.BytesIO()
            img.save(buf)
            qr = buf.getvalue().decode()
        except Exception:
            qr = ""
        cache.set("qr_download_svg", qr, 3600)
    return render(request, "public/download.html", {"qr_svg": qr})


@never_cache
def healthz(request):
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "error"}, status=503)


def manifest(request):
    data = {
        "name": "INDPNS Market", "short_name": "INDPNS", "start_url": "/?source=pwa", "scope": "/",
        "display": "standalone", "background_color": "#F8F9FA", "theme_color": "#2563EB",
        "description": "Professional marketplace for digital products.",
        "icons": [
            {"src": static("icons/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("icons/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("icons/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return HttpResponse(json.dumps(data), content_type="application/manifest+json")


def service_worker(request):
    p = Path(settings.BASE_DIR) / "static" / "js" / "service-worker.js"
    resp = HttpResponse(p.read_text(encoding="utf-8"), content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


def offline(request):
    return render(request, "public/offline.html")


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)
