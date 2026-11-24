import uuid

from django.db import models


class PaymentTransaction(models.Model):
    STATUS = [("pending", "Pending"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("refunded", "Refunded")]
    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="transactions")
    provider = models.CharField(max_length=20)
    provider_ref = models.CharField(max_length=120, blank=True, db_index=True)
    payment_ref = models.CharField(max_length=120, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class WebhookEvent(models.Model):
    provider = models.CharField(max_length=20)
    event_id = models.CharField(max_length=120)
    event_type = models.CharField(max_length=80)
    processed = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "event_id")
        ordering = ["-received_at"]
