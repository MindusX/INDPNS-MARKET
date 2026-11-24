from django.db import transaction
from django.utils.translation import gettext as _

from apps.core.services import audit
from apps.notifications.services import notify
from apps.products.services import mark_published

from .models import ModerationDecision


class ModerationError(Exception):
    pass


@transaction.atomic
def decide(product, moderator, decision, reason="", request=None):
    st = product.status
    if decision == "approved":
        if st != "pending":
            raise ModerationError(_("Only pending products can be approved."))
        if not any(v.is_safe for v in product.versions.all()):
            raise ModerationError(_("No file has passed security checks."))
        mark_published(product)
    elif decision == "rejected":
        if st != "pending":
            raise ModerationError(_("Only pending products can be rejected."))
        if not reason.strip():
            raise ModerationError(_("A reason is required."))
        product.status, product.rejection_reason = "rejected", reason
        product.save(update_fields=["status", "rejection_reason", "updated_at"])
    elif decision == "suspended":
        if st != "approved":
            raise ModerationError(_("Only published products can be suspended."))
        if not reason.strip():
            raise ModerationError(_("A reason is required."))
        product.status, product.rejection_reason = "suspended", reason
        product.save(update_fields=["status", "rejection_reason", "updated_at"])
    elif decision == "reinstated":
        if st != "suspended":
            raise ModerationError(_("Only suspended products can be reinstated."))
        product.status = "approved"
        product.save(update_fields=["status", "updated_at"])
    else:
        raise ModerationError("Unknown decision")
    d = ModerationDecision.objects.create(product=product, moderator=moderator, decision=decision, reason=reason)
    audit(moderator, f"moderation.{decision}", product, request, reason=reason[:100])
    notify(product.shop.user, "product_status", _("Your product “%(t)s”: %(s)s") % {"t": product.title, "s": decision}, reason[:200], product.get_absolute_url())
    return d
