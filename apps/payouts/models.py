from django.conf import settings
from django.db import models


class Payout(models.Model):
    STATUS = [("requested", "Requested"), ("approved", "Approved"), ("paid", "Paid"), ("rejected", "Rejected")]
    shop = models.ForeignKey("sellers.Shop", on_delete=models.PROTECT, related_name="payouts")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=10, choices=STATUS, default="requested", db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    processed_at = models.DateTimeField(null=True, blank=True)
    provider_ref = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-requested_at"]
