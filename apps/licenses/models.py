import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class LicenseType(models.Model):
    code = models.SlugField(unique=True)   # personal | commercial | extended
    name = models.CharField(max_length=60)
    summary = models.CharField(max_length=200)
    rights = models.JSONField(default=list, help_text="Liste de droits accordés")
    restrictions = models.JSONField(default=list, help_text="Liste de restrictions")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class ProductLicensePrice(models.Model):
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="license_prices")
    license_type = models.ForeignKey(LicenseType, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("product", "license_type")
        ordering = ["license_type__sort_order"]


class License(models.Model):
    """Licence émise à l'achat. Donne accès permanent aux versions du produit tant qu'elle n'est pas révoquée."""
    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="licenses")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="licenses")
    license_type = models.ForeignKey(LicenseType, on_delete=models.PROTECT)
    order_item = models.OneToOneField("orders.OrderItem", on_delete=models.PROTECT, related_name="license")
    issued_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    @property
    def is_active(self):
        return self.revoked_at is None
