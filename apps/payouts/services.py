from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.commissions.services import record_payout, seller_available
from apps.core.services import audit
from apps.notifications.services import notify

from .models import Payout


class PayoutError(Exception):
    pass


@transaction.atomic
def request_payout(shop, amount):
    if not shop.is_payout_eligible:
        raise PayoutError(_("Payouts require a verified identity (KYC). Complete verification first."))
    amount = Decimal(amount).quantize(Decimal("0.01"))
    if amount < Decimal(settings.MIN_PAYOUT_AMOUNT):
        raise PayoutError(_("Minimum payout is %(m)s.") % {"m": settings.MIN_PAYOUT_AMOUNT})
    if amount > seller_available(shop):
        raise PayoutError(_("Amount exceeds your available balance."))
    return Payout.objects.create(shop=shop, amount=amount)


@transaction.atomic
def approve_payout(payout_id, admin_user, request=None):
    p = Payout.objects.select_for_update().get(pk=payout_id)
    if p.status != "requested":
        raise PayoutError(_("This payout was already processed."))
    if not p.shop.is_payout_eligible:
        raise PayoutError(_("The shop is not KYC-verified."))
    p.status, p.processed_by, p.processed_at = "approved", admin_user, timezone.now()
    p.save()
    record_payout(p)
    audit(admin_user, "payout.approved", p, request, amount=p.amount)
    return p


@transaction.atomic
def mark_paid(payout_id, admin_user, provider_ref="", request=None):
    p = Payout.objects.select_for_update().get(pk=payout_id)
    if p.status != "approved":
        raise PayoutError(_("Only approved payouts can be marked as paid."))
    p.status, p.provider_ref = "paid", provider_ref[:120]
    p.save()
    notify(p.shop.user, "payout", _("Payout sent"), f"{p.amount} {p.currency}", "")
    audit(admin_user, "payout.paid", p, request, ref=provider_ref)
    return p


@transaction.atomic
def reject_payout(payout_id, admin_user, note="", request=None):
    p = Payout.objects.select_for_update().get(pk=payout_id)
    if p.status != "requested":
        raise PayoutError(_("This payout was already processed."))
    p.status, p.note, p.processed_by, p.processed_at = "rejected", note[:300], admin_user, timezone.now()
    p.save()
    audit(admin_user, "payout.rejected", p, request)
    return p
