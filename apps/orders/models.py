import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class Order(models.Model):
    STATUS = [("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed"), ("cancelled", "Cancelled"), ("refunded", "Refunded")]
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending", db_index=True)
    currency = models.CharField(max_length=3, default="USD")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    provider = models.CharField(max_length=20, blank=True)       # stripe | paypal | free
    provider_ref = models.CharField(max_length=120, blank=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="order_items")
    shop = models.ForeignKey("sellers.Shop", on_delete=models.PROTECT, related_name="order_items")
    license_type = models.ForeignKey("licenses.LicenseType", on_delete=models.PROTECT)
    title_snapshot = models.CharField(max_length=160)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    seller_amount = models.DecimalField(max_digits=10, decimal_places=2)


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="invoice")
    number = models.CharField(max_length=30, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)


class DownloadLog(models.Model):
    license = models.ForeignKey("licenses.License", on_delete=models.CASCADE, related_name="downloads")
    version = models.ForeignKey("products.ProductVersion", on_delete=models.CASCADE, related_name="+")
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
