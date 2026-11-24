from django.db import models


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kw):
        raise RuntimeError("Ledger entries are immutable.")

    def delete(self):
        raise RuntimeError("Ledger entries are immutable.")

    def bulk_update(self, *a, **kw):
        raise RuntimeError("Ledger entries are immutable.")


class LedgerEntry(models.Model):
    """Journal comptable append-only. Le solde = somme des écritures (aucun champ balance mutable)."""
    TYPES = [("sale_earning", "Sale earning"), ("platform_commission", "Platform commission"),
             ("refund_earning", "Refund (seller)"), ("refund_commission", "Refund (platform)"),
             ("payout", "Payout")]
    shop = models.ForeignKey("sellers.Shop", null=True, blank=True, on_delete=models.PROTECT, related_name="ledger")  # null = plateforme
    entry_type = models.CharField(max_length=24, choices=TYPES, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)   # signé : crédit > 0, débit < 0
    currency = models.CharField(max_length=3, default="USD")
    order_item = models.ForeignKey("orders.OrderItem", null=True, blank=True, on_delete=models.PROTECT, related_name="ledger")
    reference = models.CharField(max_length=60, blank=True)
    idempotency_key = models.CharField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *a, **kw):
        if self.pk:
            raise RuntimeError("Ledger entries are immutable.")
        return super().save(*a, **kw)

    def delete(self, *a, **kw):
        raise RuntimeError("Ledger entries are immutable.")
