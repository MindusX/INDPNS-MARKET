from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.forms import ProfileForm
from apps.accounts.models import ROLE_ORDER, LoginEvent, User, UserSession
from apps.commissions.models import LedgerEntry
from apps.commissions.services import platform_revenue, seller_available, seller_balance
from apps.core.models import AuditLog
from apps.core.permissions import seller_required, staff_role_required
from apps.core.ratelimit import ratelimit
from apps.core.services import audit
from apps.licenses.models import License
from apps.moderation.services import ModerationError, decide
from apps.notifications.models import Notification
from apps.orders.models import Order, OrderItem
from apps.orders.services import OrderError, refund_order
from apps.payouts.models import Payout
from apps.payouts.services import PayoutError, approve_payout, mark_paid, reject_payout, request_payout
from apps.products.forms import (DescriptionForm, GalleryForm, InfoForm, MediaForm, PricingForm,
                                 TechForm, VersionForm)
from apps.products.models import Favorite, Product, ProductImage, ProductReport
from apps.products.services import add_version, submission_problems, submit_for_moderation
from apps.reviews.models import Review
from apps.sellers.forms import ShopForm, ShopLogoForm

from .navigation import context


def paginate(request, qs, n=20):
    return Paginator(qs, n).get_page(request.GET.get("page"))


@login_required
def home(request):
    u = request.user
    if u.is_internal:
        return redirect("dashboard:admin_home")
    if u.is_seller:
        return redirect("dashboard:seller_home")
    return redirect("dashboard:buyer_home")


@login_required
@require_POST
def set_theme(request):
    t = request.POST.get("theme")
    if t in ("light", "dark"):
        request.user.theme = t
        request.user.save(update_fields=["theme"])
    return JsonResponse({"ok": True})


# ======================= BUYER =======================
@login_required
def buyer_home(request):
    u = request.user
    return render(request, "dashboard/buyer/home.html", context(request, "buyer",
        n_licenses=License.objects.filter(buyer=u, revoked_at__isnull=True).count(),
        n_orders=Order.objects.filter(buyer=u, status="paid").count(),
        n_favorites=Favorite.objects.filter(user=u).count(),
        recent=License.objects.filter(buyer=u).select_related("product", "license_type")[:5]))


@login_required
def buyer_library(request):
    lics = License.objects.filter(buyer=request.user).select_related("product__shop", "license_type").prefetch_related("product__versions", "review")
    rows = [{"license": l, "versions": [v for v in l.product.versions.all() if v.is_safe],
             "reviewed": hasattr(l, "review")} for l in paginate(request, lics, 12)]
    return render(request, "dashboard/buyer/library.html", context(request, "buyer", rows=rows, page=paginate(request, lics, 12)))


@login_required
def buyer_orders(request):
    page = paginate(request, Order.objects.filter(buyer=request.user).prefetch_related("items"))
    return render(request, "dashboard/buyer/orders.html", context(request, "buyer", page=page))


@login_required
def buyer_order(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items__product"), number=number, buyer=request.user)
    return render(request, "dashboard/buyer/order_detail.html", context(request, "buyer", order=order))


@login_required
def buyer_favorites(request):
    page = paginate(request, Favorite.objects.filter(user=request.user, product__status="approved").select_related("product__shop"), 24)
    return render(request, "dashboard/buyer/favorites.html", context(request, "buyer", page=page))


@login_required
def buyer_reviews(request):
    page = paginate(request, Review.objects.filter(user=request.user).select_related("product"))
    return render(request, "dashboard/buyer/reviews.html", context(request, "buyer", page=page))


@login_required
def buyer_notifications(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return redirect("dashboard:buyer_notifications")
    page = paginate(request, Notification.objects.filter(user=request.user))
    return render(request, "dashboard/buyer/notifications.html", context(request, "buyer", page=page))


@login_required
def buyer_security(request):
    u = request.user
    return render(request, "dashboard/buyer/security.html", context(request, "buyer",
        sessions=UserSession.objects.filter(user=u), current_key=request.session.session_key,
        events=LoginEvent.objects.filter(user=u)[:15]))


@login_required
@ratelimit("profile", limit=40, window=600)
def buyer_profile(request):
    """Profil avancé : identité publique, photo, couverture, liens, visibilité (multipart)."""
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        audit(user, "user.profile_updated", user, request, public=user.profile_public)
        messages.success(request, _("Profile saved."))
        return redirect("dashboard:buyer_profile")
    if request.method == "POST":
        messages.error(request, _("Please fix the highlighted fields."))
    return render(request, "dashboard/buyer/profile.html", context(request, "buyer", form=form, profile_user=request.user,
                   profile_url=request.build_absolute_uri(request.user.get_public_url()) if request.user.username else ""))


# ======================= SELLER =======================
@seller_required
def seller_home(request):
    shop = request.user.shop
    items = OrderItem.objects.filter(shop=shop, order__status="paid")
    agg = items.aggregate(n=Count("id"), gross=Sum("unit_price"), net=Sum("seller_amount"))
    by_status = dict(Product.objects.filter(shop=shop).values_list("status").annotate(c=Count("id")))
    return render(request, "dashboard/seller/home.html", context(request, "seller", shop=shop,
        n_sales=agg["n"] or 0, gross=agg["gross"] or Decimal("0"), net=agg["net"] or Decimal("0"),
        balance=seller_balance(shop), available=seller_available(shop), by_status=by_status,
        problems_hint=not shop.is_payout_eligible))


@seller_required
def seller_shop(request):
    shop = request.user.shop
    form = ShopForm(request.POST or None, instance=shop, prefix="s")
    lform = ShopLogoForm(request.POST or None, request.FILES or None, instance=shop, prefix="l")
    if request.method == "POST":
        f = lform if "l-logo" in request.FILES else form
        if f.is_valid():
            f.save()
            messages.success(request, _("Shop updated."))
            return redirect("dashboard:seller_shop")
    return render(request, "dashboard/seller/shop.html", context(request, "seller", form=form, lform=lform, shop=shop))


@seller_required
def seller_products(request):
    page = paginate(request, Product.objects.filter(shop=request.user.shop))
    return render(request, "dashboard/seller/products.html", context(request, "seller", page=page))


STEPS = [("info", _("Basics")), ("description", _("Description")), ("tech", _("Tech & compatibility")),
         ("media", _("Media")), ("files", _("Files")), ("pricing", _("Pricing & licenses")), ("review", _("Review & submit"))]
STEP_FORMS = {"info": InfoForm, "description": DescriptionForm, "tech": TechForm, "media": MediaForm}


def _editable_steps(product):
    if product.status in ("draft", "rejected"):
        return {s for s, _l in STEPS}
    if product.status == "approved":
        return {"files", "pricing", "review"}
    return {"review"}


@seller_required
def product_new(request):
    form = InfoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        from apps.core.utils import unique_slug
        p = form.save(commit=False)
        p.shop, p.slug = request.user.shop, unique_slug(Product, p.title, max_len=70)
        p.save()
        return redirect("dashboard:product_edit", pk=p.pk, step="description")
    return render(request, "dashboard/seller/product_edit.html", context(request, "seller", form=form, product=None, step="info", steps=STEPS, editable=True))


@seller_required
def product_edit(request, pk, step="info"):
    product = get_object_or_404(Product.objects.prefetch_related("versions", "images"), pk=pk, shop=request.user.shop)
    keys = [s for s, _l in STEPS]
    if step not in keys:
        raise Http404
    editable = step in _editable_steps(product)
    form, extra = None, {}
    if step in STEP_FORMS:
        Form = STEP_FORMS[step]
        if request.method == "POST" and editable and request.POST.get("action") != "gallery":
            form = Form(request.POST, request.FILES, instance=product)
            if form.is_valid():
                form.save()
                messages.success(request, _("Saved."))
                return redirect("dashboard:product_edit", pk=product.pk, step=keys[keys.index(step) + 1])
        else:
            form = Form(instance=product)
        if step == "media":
            gform = GalleryForm(request.POST or None, request.FILES or None)
            if request.method == "POST" and editable and request.POST.get("action") == "gallery" and gform.is_valid():
                img = gform.save(commit=False)
                img.product = product
                img.save()
                return redirect("dashboard:product_edit", pk=product.pk, step="media")
            extra["gform"] = gform
    elif step == "files":
        form = VersionForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and editable and form.is_valid():
            add_version(product, form.cleaned_data["file"], form.cleaned_data["version"], form.cleaned_data["changelog"])
            messages.success(request, _("File uploaded. It is checked before it can be published."))
            return redirect("dashboard:product_edit", pk=product.pk, step="files")
    elif step == "pricing":
        form = PricingForm(request.POST or None, product=product)
        if request.method == "POST" and editable and form.is_valid():
            form.save()
            messages.success(request, _("Pricing saved."))
            return redirect("dashboard:product_edit", pk=product.pk, step="review")
    elif step == "review":
        extra["problems"] = submission_problems(product)
        if request.method == "POST":
            if product.status not in ("draft", "rejected"):
                raise PermissionDenied
            problems = submit_for_moderation(product)
            if problems:
                messages.error(request, _("Please fix the issues below before submitting."))
            else:
                messages.success(request, _("Submitted. Our moderators will review it; it is not public until approved."))
                return redirect("dashboard:seller_products")
            extra["problems"] = problems
    return render(request, "dashboard/seller/product_edit.html", context(request, "seller", product=product, step=step, steps=STEPS,
                                                                           form=form, editable=editable, **extra))


@seller_required
@require_POST
def product_image_delete(request, pk, image_id):
    product = get_object_or_404(Product, pk=pk, shop=request.user.shop)
    if product.status in ("draft", "rejected"):
        ProductImage.objects.filter(pk=image_id, product=product).delete()
    return redirect("dashboard:product_edit", pk=pk, step="media")


@seller_required
@require_POST
def product_archive(request, pk):
    product = get_object_or_404(Product, pk=pk, shop=request.user.shop)
    product.status = "archived"
    product.save(update_fields=["status", "updated_at"])
    audit(request.user, "product.archived", product, request)
    messages.success(request, _("Product archived. Existing buyers keep their access."))
    return redirect("dashboard:seller_products")


@seller_required
def seller_sales(request):
    page = paginate(request, OrderItem.objects.filter(shop=request.user.shop, order__status__in=("paid", "refunded")).select_related("order", "product").order_by("-order__created_at"))
    return render(request, "dashboard/seller/sales.html", context(request, "seller", page=page))


@seller_required
def seller_revenue(request):
    shop = request.user.shop
    page = paginate(request, LedgerEntry.objects.filter(shop=shop))
    return render(request, "dashboard/seller/revenue.html", context(request, "seller", page=page, balance=seller_balance(shop), available=seller_available(shop), shop=shop))


@seller_required
def seller_payouts(request):
    shop = request.user.shop
    if request.method == "POST":
        try:
            request_payout(shop, request.POST.get("amount", "0"))
            messages.success(request, _("Payout requested."))
        except (PayoutError, ArithmeticError, ValueError) as e:
            messages.error(request, str(e) if isinstance(e, PayoutError) else _("Invalid amount."))
        return redirect("dashboard:seller_payouts")
    return render(request, "dashboard/seller/payouts.html", context(request, "seller", shop=shop, page=paginate(request, Payout.objects.filter(shop=shop)),
                                                                     available=seller_available(shop)))


@seller_required
def seller_reviews(request):
    page = paginate(request, Review.objects.filter(product__shop=request.user.shop).select_related("product", "user"))
    return render(request, "dashboard/seller/reviews.html", context(request, "seller", page=page))


@seller_required
def seller_verification(request):
    shop = request.user.shop
    if request.method == "POST" and shop.verification_status in ("none", "rejected"):
        shop.verification_status = "pending"
        shop.save(update_fields=["verification_status"])
        audit(request.user, "seller.verification_requested", shop, request)
        messages.success(request, _("Verification requested. Our team will review your shop."))
        return redirect("dashboard:seller_verification")
    return render(request, "dashboard/seller/verification.html", context(request, "seller", shop=shop))


# ======================= ADMIN / STAFF =======================
@staff_role_required("moderator")
def admin_home(request):
    paid = Order.objects.filter(status="paid")
    return render(request, "dashboard/admin/home.html", context(request, "admin",
        n_users=User.objects.count(), n_sellers=User.objects.filter(shop__isnull=False).count(),
        n_buyers=User.objects.filter(licenses__isnull=False).distinct().count(),
        products=dict(Product.objects.values_list("status").annotate(c=Count("id"))),
        n_orders=paid.count(), gmv=paid.aggregate(s=Sum("total"))["s"] or Decimal("0"),
        revenue=platform_revenue(), n_refunds=Order.objects.filter(status="refunded").count(),
        pending_payouts=Payout.objects.filter(status="requested").count(),
        open_reports=ProductReport.objects.filter(status="open").count(),
        recent=AuditLog.objects.select_related("actor")[:8] if request.user.has_role_at_least("admin") else []))


@staff_role_required("moderator")
def admin_moderation(request):
    status = request.GET.get("status", "pending")
    qs = Product.objects.filter(status=status).select_related("shop", "category").order_by("created_at")
    return render(request, "dashboard/admin/moderation.html", context(request, "admin", page=paginate(request, qs), status=status))


@staff_role_required("moderator")
def admin_moderation_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("shop", "category").prefetch_related("versions", "images", "decisions__moderator", "technologies"), pk=pk)
    if request.method == "POST":
        try:
            decide(product, request.user, request.POST.get("decision", ""), request.POST.get("reason", ""), request)
            messages.success(request, _("Decision recorded."))
            return redirect("dashboard:admin_moderation")
        except ModerationError as e:
            messages.error(request, str(e))
    return render(request, "dashboard/admin/moderation_detail.html", context(request, "admin", product=product))


@staff_role_required("admin")
def admin_users(request):
    q = request.GET.get("q", "").strip()
    qs = User.objects.all()
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(display_name__icontains=q))
    if request.method == "POST":
        target = get_object_or_404(User, pk=request.POST.get("user_id"))
        role, action = request.POST.get("role"), request.POST.get("action")
        if target.is_superuser and not request.user.is_superuser:
            raise PermissionDenied
        if action == "role" and role in ROLE_ORDER:
            top_roles = ("admin", "superadmin")
            if role in top_roles and not request.user.is_superuser:
                raise PermissionDenied
            target.role = role
            target.is_staff = role in ("moderator", "support", "admin", "superadmin")
            target.save(update_fields=["role", "is_staff"])
            audit(request.user, "user.role_changed", target, request, role=role)
        elif action == "toggle_active" and target.pk != request.user.pk:
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            audit(request.user, "user.active_toggled", target, request, active=target.is_active)
        return redirect(request.get_full_path())
    return render(request, "dashboard/admin/users.html", context(request, "admin", page=paginate(request, qs), q=q, roles=ROLE_ORDER))


@staff_role_required("admin")
def admin_orders(request):
    if request.method == "POST":
        try:
            refund_order(request.POST.get("order_id"), request.user, request)
            messages.success(request, _("Order refunded."))
        except (OrderError, Exception) as e:   # PaymentError et OrderError : message sûr
            messages.error(request, str(e) if isinstance(e, OrderError) else _("The refund failed. Check the provider dashboard."))
        return redirect("dashboard:admin_orders")
    qs = Order.objects.select_related("buyer").prefetch_related("items")
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    return render(request, "dashboard/admin/orders.html", context(request, "admin", page=paginate(request, qs)))


@staff_role_required("admin")
def admin_payouts(request):
    if request.method == "POST":
        action, pid = request.POST.get("action"), request.POST.get("payout_id")
        try:
            if action == "approve":
                approve_payout(pid, request.user, request)
            elif action == "paid":
                mark_paid(pid, request.user, request.POST.get("provider_ref", ""), request)
            elif action == "reject":
                reject_payout(pid, request.user, request.POST.get("note", ""), request)
            messages.success(request, _("Payout updated."))
        except PayoutError as e:
            messages.error(request, str(e))
        return redirect("dashboard:admin_payouts")
    qs = Payout.objects.select_related("shop")
    return render(request, "dashboard/admin/payouts.html", context(request, "admin", page=paginate(request, qs)))


@staff_role_required("support")
def admin_reports(request):
    if request.method == "POST":
        ProductReport.objects.filter(pk=request.POST.get("report_id")).update(status="closed")
        audit(request.user, "report.closed", None, request, id=request.POST.get("report_id"))
        return redirect("dashboard:admin_reports")
    page = paginate(request, ProductReport.objects.select_related("product", "reporter").filter(status=request.GET.get("status", "open")))
    return render(request, "dashboard/admin/reports.html", context(request, "admin", page=page))


@staff_role_required("admin")
def admin_audit(request):
    return render(request, "dashboard/admin/audit.html", context(request, "admin", page=paginate(request, AuditLog.objects.select_related("actor"), 40)))
