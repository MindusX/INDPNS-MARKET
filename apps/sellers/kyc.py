"""Vérification d'identité (KYC) — soumission, validation et refus par l'équipe.

Cycle : none/rejected -> pending (le vendeur envoie son dossier) -> verified | rejected (décision d'un administrateur).
Seul `shop.kyc_status == "verified"` débloque les retraits (voir Shop.is_payout_eligible)."""
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core.crypto import decrypt_bytes, encrypt_bytes, encryption_available
from apps.core.services import audit
from apps.notifications.services import notify

from .kyc_images import MIME
from .models import IdentityVerification, KycDocument, Shop


class KycError(Exception):
    pass


def can_submit(shop):
    return shop.kyc_status in ("none", "rejected") and not shop.identity_checks.filter(status="pending").exists()


@transaction.atomic
def submit_verification(shop, data, images, request=None):
    """data : champs du dossier ; images : {"front": bytes, "back": bytes|None, "selfie": bytes} (JPEG déjà traités)."""
    if not encryption_available():
        raise KycError(_("Identity verification is temporarily unavailable. Please contact support."))
    shop = Shop.objects.select_for_update().get(pk=shop.pk)
    if shop.kyc_status == "verified":
        raise KycError(_("Your identity is already verified."))
    if shop.identity_checks.filter(status="pending").exists():
        raise KycError(_("Your verification is already being reviewed."))
    try:
        with transaction.atomic():
            v = IdentityVerification.objects.create(shop=shop, **data)
    except IntegrityError:
        raise KycError(_("Your verification is already being reviewed."))
    for kind, raw in images.items():
        if raw:
            KycDocument.objects.create(verification=v, kind=kind, data=encrypt_bytes(raw), mime=MIME)
    shop.kyc_status = "pending"
    shop.save(update_fields=["kyc_status"])
    audit(shop.user, "kyc.submitted", v, request, doc_type=v.doc_type)
    return v


def document_bytes(doc):
    """Déchiffre une image (réservé aux vues d'administration, qui écrivent une entrée d'audit)."""
    if not doc.data:
        raise KycError(_("This document has been deleted."))
    return decrypt_bytes(doc.data)


def purge_documents(verification):
    return KycDocument.objects.filter(verification=verification).update(data=None)


@transaction.atomic
def approve(verification_id, admin_user, request=None):
    v = IdentityVerification.objects.select_for_update().select_related("shop", "shop__user").get(pk=verification_id)
    if v.status != "pending":
        raise KycError(_("This request was already processed."))
    v.status, v.reviewed_by, v.reviewed_at, v.rejection_reason = "approved", admin_user, timezone.now(), ""
    v.save()
    v.shop.kyc_status = "verified"
    v.shop.save(update_fields=["kyc_status"])
    if getattr(settings, "KYC_PURGE_DOCS_ON_APPROVAL", False):
        purge_documents(v)
    audit(admin_user, "kyc.approved", v, request)
    notify(v.shop.user, "kyc", _("Identity verified"), _("Your identity has been verified. You can now request payouts."), "/dashboard/seller/payouts/")
    return v


@transaction.atomic
def reject(verification_id, admin_user, reason, request=None):
    reason = (reason or "").strip()
    if not reason:
        raise KycError(_("A reason is required."))
    v = IdentityVerification.objects.select_for_update().select_related("shop", "shop__user").get(pk=verification_id)
    if v.status != "pending":
        raise KycError(_("This request was already processed."))
    v.status, v.reviewed_by, v.reviewed_at, v.rejection_reason = "rejected", admin_user, timezone.now(), reason[:1000]
    v.save()
    v.shop.kyc_status = "rejected"
    v.shop.save(update_fields=["kyc_status"])
    audit(admin_user, "kyc.rejected", v, request, reason=reason[:100])
    notify(v.shop.user, "kyc", _("Identity verification: action needed"), reason[:200], "/dashboard/seller/verification/")
    return v
