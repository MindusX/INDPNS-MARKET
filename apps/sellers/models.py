from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
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


class IdentityVerification(models.Model):
    """Dossier de vérification d'identité (KYC) d'un vendeur — comme sur les autres places de marché.
    Une seule demande « en attente » à la fois ; après un refus, le vendeur peut en soumettre une nouvelle.
    Les images (recto, verso, selfie) sont dans KycDocument, CHIFFRÉES, et jamais servies publiquement."""
    STATUS = [("pending", _("Pending review")), ("approved", _("Approved")), ("rejected", _("Rejected"))]
    DOC_TYPES = [("passport", _("Passport")), ("national_id", _("National ID card")), ("driver_license", _("Driver's licence"))]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="identity_checks")
    status = models.CharField(max_length=10, choices=STATUS, default="pending", db_index=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=2)
    address_line1 = models.CharField(max_length=120)
    address_line2 = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80)
    region = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2)
    phone = models.CharField(max_length=30, blank=True)
    doc_type = models.CharField(max_length=16, choices=DOC_TYPES)
    doc_country = models.CharField(max_length=2)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [models.UniqueConstraint(fields=["shop"], condition=models.Q(status="pending"), name="one_pending_identity_per_shop")]

    def __str__(self):
        return f"KYC {self.pk} — {self.shop} ({self.status})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class KycDocument(models.Model):
    """Image d'une pièce d'identité. `data` = JPEG CHIFFRÉ (Fernet). Jamais exposée par une URL publique :
    seuls les administrateurs peuvent la voir, via une vue authentifiée qui écrit une entrée d'audit à chaque consultation."""
    KINDS = [("front", _("Document — front")), ("back", _("Document — back")), ("selfie", _("Selfie holding your document"))]

    verification = models.ForeignKey(IdentityVerification, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=8, choices=KINDS)
    data = models.BinaryField(null=True, blank=True, editable=False)
    mime = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["verification", "kind"], name="one_document_per_kind")]

    @property
    def is_purged(self):
        return not self.data
