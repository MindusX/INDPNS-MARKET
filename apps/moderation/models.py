from django.conf import settings
from django.db import models


class ModerationDecision(models.Model):
    DECISIONS = [("approved", "Approved"), ("rejected", "Rejected"), ("suspended", "Suspended"), ("reinstated", "Reinstated")]
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="decisions")
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    decision = models.CharField(max_length=12, choices=DECISIONS)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
