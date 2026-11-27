from django.contrib import admin

from .models import IdentityVerification, SellerPlan, Shop


@admin.register(SellerPlan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_monthly", "price_yearly", "commission_rate", "is_active", "sort_order")


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "plan", "verification_status", "kyc_status", "is_active")
    list_filter = ("plan", "verification_status", "kyc_status", "is_active")
    search_fields = ("name", "user__email")


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    """Lecture seule : les images (KycDocument) ne sont volontairement PAS exposées dans l'admin Django ;
    leur consultation passe par Dashboard > Admin > Identity checks, qui journalise chaque accès."""
    list_display = ("shop", "first_name", "last_name", "country", "doc_type", "status", "submitted_at")
    list_filter = ("status", "doc_type")
    search_fields = ("shop__name", "first_name", "last_name")
    readonly_fields = [f.name for f in IdentityVerification._meta.fields]

    def has_add_permission(self, request):
        return False
