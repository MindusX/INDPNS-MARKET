from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


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
    # Destination figée au moment de la demande (le vendeur peut changer de moyen de paiement ensuite) : visible par l'admin qui verse l'argent.
    method_kind = models.CharField(max_length=12, blank=True)
    destination = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["-requested_at"]


class PayoutMethod(models.Model):
    """Compte de réception des gains du vendeur, connecté par redirection (comme « Continuer avec Facebook ») :
       - paypal : connexion « Log in with PayPal » (OAuth / OpenID Connect) ; on ne stocke que l'identifiant PayPal et l'e-mail ;
       - stripe : Stripe Connect (Express) — Stripe collecte la carte bancaire ou le compte bancaire ; on ne stocke QUE
         l'identifiant du compte Stripe et les 4 derniers chiffres. Aucun numéro de carte / IBAN ne transite par nos serveurs."""
    KINDS = [("paypal", "PayPal"), ("stripe", _("Bank card / account"))]
    STATUS = [("pending", _("Setup incomplete")), ("connected", _("Connected")), ("restricted", _("Under review"))]

    shop = models.ForeignKey("sellers.Shop", on_delete=models.CASCADE, related_name="payout_methods")
    kind = models.CharField(max_length=12, choices=KINDS)
    external_id = models.CharField(max_length=120)            # payer_id PayPal ou acct_… Stripe
    label = models.CharField(max_length=160, blank=True)      # « PayPal · jean@exemple.com » / « Visa •••• 4242 »
    email = models.EmailField(blank=True)
    brand = models.CharField(max_length=40, blank=True)       # Visa, Mastercard, nom de la banque…
    last4 = models.CharField(max_length=4, blank=True)
    country = models.CharField(max_length=2, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    payouts_enabled = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "kind"]
        constraints = [
            models.UniqueConstraint(fields=["shop", "kind"], name="payoutmethod_one_per_kind"),
            models.UniqueConstraint(fields=["kind", "external_id"], name="payoutmethod_unique_account"),   # un compte = une boutique
        ]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.label}"

    @property
    def is_usable(self):
        return self.status == "connected" and self.payouts_enabled
