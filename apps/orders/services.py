import uuid
from decimal import Decimal

from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.commissions.services import record_refund, record_sale
from apps.core.services import audit
from apps.core.utils import money
from apps.licenses.models import License, ProductLicensePrice
from apps.licenses.services import issue_license, revoke_license
from apps.notifications.services import notify, send_email
from apps.sellers.services import commission_rate_for

from .models import Invoice, Order, OrderItem


class OrderError(Exception):
    pass


def _number():
    return "IM-" + uuid.uuid4().hex[:10].upper()


@transaction.atomic
def create_order(buyer, product, license_code):
    if product.status != "approved":
        raise OrderError(_("This product is not available."))
    if product.shop.user_id == buyer.pk:
        raise OrderError(_("You cannot buy your own product."))
    if License.objects.filter(buyer=buyer, product=product, revoked_at__isnull=True).exists():
        raise OrderError(_("You already own this product. Find it in your library."))
    lp = ProductLicensePrice.objects.select_related("license_type").filter(product=product, license_type__code=license_code).first()
    if lp is None:
        raise OrderError(_("This license is not offered for this product."))
    existing = Order.objects.filter(buyer=buyer, status="pending", items__product=product, items__license_type=lp.license_type).first()
    if existing:
        return existing
    price = money(lp.price)
    rate = commission_rate_for(product.shop) if price > 0 else Decimal("0")
    commission = money(price * rate)
    order = Order.objects.create(buyer=buyer, number=_number(), subtotal=price, total=price)
    OrderItem.objects.create(order=order, product=product, shop=product.shop, license_type=lp.license_type,
                             title_snapshot=f"{product.title} — {lp.license_type.name}", unit_price=price,
                             commission_rate=rate, commission_amount=commission, seller_amount=price - commission)
    return order


@transaction.atomic
def mark_order_paid(order_id, provider, provider_ref=""):
    """Idempotent : un second appel (webhook rejoué) ne fait rien. Retourne (order, changed)."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == "paid":
        return order, False
    if order.status != "pending":
        raise OrderError(f"Order {order.number} is {order.status}")
    order.status, order.provider, order.provider_ref, order.paid_at = "paid", provider, provider_ref, timezone.now()
    order.save()
    for item in order.items.select_related("order", "product", "shop", "license_type"):
        issue_license(item)
        record_sale(item)
        notify(item.shop.user, "sale", _("New sale: %(t)s") % {"t": item.product.title}, f"{item.seller_amount} {order.currency}", "")
    Invoice.objects.get_or_create(order=order, defaults={"number": f"INV-{order.paid_at.year}-{order.pk:06d}"})
    notify(order.buyer, "order", _("Order %(n)s confirmed") % {"n": order.number}, "", reverse("dashboard:buyer_order", args=[order.number]))
    transaction.on_commit(lambda: send_email(order.buyer.email, _("Your INDPNS Market order %(n)s") % {"n": order.number},
                                            "emails/order_paid.html", {"order": order, "items": list(order.items.all())}))
    return order, True


def complete_free_order(order):
    if order.total != 0:
        raise OrderError("Order is not free")
    return mark_order_paid(order.pk, "free", "free-" + order.number)[0]


@transaction.atomic
def refund_order(order_id, actor, request=None):
    """Remboursement : appelle d'abord le prestataire (si paiement réel), puis écrit les écritures inverses."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != "paid":
        raise OrderError(_("Only paid orders can be refunded."))
    if order.provider not in ("free", "manual", ""):
        from apps.payments.registry import get_provider
        provider = get_provider()
        if provider is None or provider.name != order.provider or not provider.is_configured():
            raise OrderError(_("The payment provider is not configured; refund it at the provider first."))
        provider.refund(order)
    order.status = "refunded"
    order.save(update_fields=["status"])
    for item in order.items.select_related("order", "shop"):
        revoke_license(item)
        record_refund(item)
    audit(actor, "order.refunded", order, request, total=order.total)
    notify(order.buyer, "refund", _("Order %(n)s refunded") % {"n": order.number}, "", "")
    return order
