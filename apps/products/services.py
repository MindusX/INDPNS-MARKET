import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core.files import sha256_of
from apps.licenses.models import ProductLicensePrice

from .models import Product, ProductVersion

logger = logging.getLogger(__name__)


def refresh_base_price(product):
    prices = list(ProductLicensePrice.objects.filter(product=product).values_list("price", flat=True))
    product.base_price = min(prices) if prices else Decimal("0.00")
    product.save(update_fields=["base_price", "updated_at"])


def scan_version(version):
    """Analyse antivirus (ClamAV via clamd). Sans antivirus configuré : « skipped » (ou « pending » si ANTIVIRUS_REQUIRED)."""
    if not settings.ANTIVIRUS_ENABLED:
        version.scan_status = "pending" if settings.ANTIVIRUS_REQUIRED else "skipped"
        version.scan_detail = "Antivirus not configured"
    else:
        try:
            import clamd
            cd = clamd.ClamdNetworkSocket(settings.ANTIVIRUS_CLAMD_HOST, settings.ANTIVIRUS_CLAMD_PORT, timeout=60)
            version.file.open("rb")
            try:
                result = cd.instream(version.file)
            finally:
                version.file.close()
            status, sig = result.get("stream", ("ERROR", "no result"))
            version.scan_status = {"OK": "clean", "FOUND": "infected"}.get(status, "error")
            version.scan_detail = (sig or "")[:200] if status != "OK" else ""
        except Exception as exc:  # fichier quarantaine tant que l'analyse échoue
            logger.exception("antivirus scan failed")
            version.scan_status = "error"
            version.scan_detail = str(exc)[:200]
    version.save(update_fields=["scan_status", "scan_detail"])
    return version


@transaction.atomic
def add_version(product, uploaded, version, changelog=""):
    v = ProductVersion(product=product, version=version, changelog=changelog, file=uploaded)
    v.file_size = uploaded.size
    v.save()
    v.sha256 = sha256_of(v.file)
    v.save(update_fields=["sha256"])
    transaction.on_commit(lambda: _scan(v.pk))
    return v


def _scan(pk):
    v = ProductVersion.objects.get(pk=pk)
    scan_version(v)


def submission_problems(product):
    p = []
    if not product.title:
        p.append(_("Add a title."))
    if not product.category_id:
        p.append(_("Choose a category."))
    if len((product.description or "").strip()) < 50:
        p.append(_("Write a description of at least 50 characters."))
    if not product.cover:
        p.append(_("Upload a cover image."))
    if not any(v.is_safe for v in product.versions.all()):
        p.append(_("Upload a file that passed the security checks."))
    if not ProductLicensePrice.objects.filter(product=product, license_type__code="personal").exists():
        p.append(_("Set a price for the personal license."))
    if not product.shop.is_active:
        p.append(_("Your shop is not active."))
    return p


@transaction.atomic
def submit_for_moderation(product):
    if product.status not in ("draft", "rejected"):
        raise ValueError("Only draft or rejected products can be submitted.")
    problems = submission_problems(product)
    if problems:
        return problems
    product.status = "pending"
    product.rejection_reason = ""
    product.save(update_fields=["status", "rejection_reason", "updated_at"])
    return []


def mark_published(product):
    product.status = "approved"
    if not product.published_at:
        product.published_at = timezone.now()
    product.save(update_fields=["status", "published_at", "updated_at"])
