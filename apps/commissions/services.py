from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .models import LedgerEntry

ZERO = Decimal("0.00")


def _create(key, **fields):
    try:
        with transaction.atomic():
            return LedgerEntry.objects.create(idempotency_key=key, **fields), True
    except IntegrityError:   # même clé : opération déjà enregistrée (idempotence)
        return LedgerEntry.objects.get(idempotency_key=key), False


def record_sale(item):
    if item.seller_amount:
        _create(f"sale:{item.pk}", shop=item.shop, entry_type="sale_earning", amount=item.seller_amount, order_item=item, currency=item.order.currency)
    if item.commission_amount:
        _create(f"commission:{item.pk}", shop=None, entry_type="platform_commission", amount=item.commission_amount, order_item=item, currency=item.order.currency)


def record_refund(item):
    if item.seller_amount:
        _create(f"refund_sale:{item.pk}", shop=item.shop, entry_type="refund_earning", amount=-item.seller_amount, order_item=item, currency=item.order.currency)
    if item.commission_amount:
        _create(f"refund_commission:{item.pk}", shop=None, entry_type="refund_commission", amount=-item.commission_amount, order_item=item, currency=item.order.currency)


def record_payout(payout):
    return _create(f"payout:{payout.pk}", shop=payout.shop, entry_type="payout", amount=-payout.amount, reference=f"payout-{payout.pk}", currency=payout.currency)[0]


def seller_balance(shop):
    return LedgerEntry.objects.filter(shop=shop).aggregate(s=Sum("amount"))["s"] or ZERO


def seller_available(shop):
    """Solde retirable : gains vieux de plus de PAYOUT_HOLD_DAYS (fenêtre de remboursement) + débits."""
    cutoff = timezone.now() - timedelta(days=settings.PAYOUT_HOLD_DAYS)
    total = LedgerEntry.objects.filter(shop=shop).filter(Q(amount__lt=0) | Q(created_at__lte=cutoff)).aggregate(s=Sum("amount"))["s"] or ZERO
    from apps.payouts.models import Payout
    pending = Payout.objects.filter(shop=shop, status="requested").aggregate(s=Sum("amount"))["s"] or ZERO
    return total - pending


def platform_revenue():
    return LedgerEntry.objects.filter(shop__isnull=True).aggregate(s=Sum("amount"))["s"] or ZERO
