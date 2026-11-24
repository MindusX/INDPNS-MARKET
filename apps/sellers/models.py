from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse


class SellerPlan(models.Model):
    """Offres vendeurs. Source unique pour la page Tarifs (modifiable en admin)."""
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=40)
    tagline = models.CharField(max_length=160, blank=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    price_yearly = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.1500"),
                                          help_text="0.15 = 15 %")
    features = models.JSONField(default=list, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    contact_only = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name

    @property
    def is_free(self):
        return self.price_monthly == 0

    @property
    def yearly_saving(self):
        return max(Decimal("0.00"), self.price_monthly * 12 - self.price_yearly)

    @property
    def commission_percent(self):
        return (self.commission_rate * 100).normalize()


class Shop(models.Model):
    VERIFICATION = [("none", "Not verified"), ("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")]
    KYC = [("none", "Not started"), ("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop")
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, max_length=2000)
    country = models.CharField(max_length=2, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="shops/logos/", blank=True)
    plan = models.ForeignKey(SellerPlan, on_delete=models.PROTECT, related_name="shops")
    verification_status = models.CharField(max_length=10, choices=VERIFICATION, default="none")
    kyc_status = models.CharField(max_length=10, choices=KYC, default="none")   # défini uniquement via le prestataire / admin
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("sellers:detail", args=[self.slug])

    @property
    def is_payout_eligible(self):
        return self.kyc_status == "verified" and self.is_active
