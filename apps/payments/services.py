import logging

from django.urls import reverse

from apps.orders.models import Order
from apps.orders.services import OrderError, mark_order_paid

from .models import PaymentTransaction
from .providers.base import PaymentError
from .providers.stripe_provider import to_cents
from .registry import get_provider

logger = logging.getLogger(__name__)


def start_checkout(order, request):
    provider = get_provider()
    if provider is None or not provider.is_configured():
        raise PaymentError("Payments are not configured.")
    success = request.build_absolute_uri(reverse("dashboard:buyer_order", args=[order.number]))
    cancel = request.build_absolute_uri(order.items.first().product.get_absolute_url())
    result = provider.create_checkout(order, success, cancel)
    PaymentTransaction.objects.update_or_create(
        order=order, provider=provider.name, status="pending",
        defaults={"provider_ref": result.provider_ref, "amount": order.total, "currency": order.currency})
    return result.url


def process_webhook(result):
    """Traite un évènement vérifié. Idempotent : mark_order_paid ne rejoue jamais un paiement déjà enregistré."""
    if not (result.paid and result.order_number):
        return
    order = Order.objects.filter(number=result.order_number).first()
    if order is None:
        logger.warning("webhook for unknown order %s", result.order_number)
        return
    if result.amount_cents is not None and result.amount_cents != to_cents(order.total):
        logger.error("amount mismatch on %s: provider=%s expected=%s", order.number, result.amount_cents, to_cents(order.total))
        raise PaymentError("Amount mismatch")
    try:
        mark_order_paid(order.pk, get_provider().name, result.provider_ref)
    except OrderError:
        logger.warning("order %s not payable (status)", order.number)
        return
    PaymentTransaction.objects.filter(order=order, provider=get_provider().name).update(
        status="succeeded", payment_ref=result.payment_ref, provider_ref=result.provider_ref or "")
