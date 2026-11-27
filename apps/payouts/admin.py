from django.contrib import admin

from .models import Payout, PayoutMethod

admin.site.register(Payout)


@admin.register(PayoutMethod)
class PayoutMethodAdmin(admin.ModelAdmin):
    list_display = ("shop", "kind", "label", "status", "payouts_enabled", "is_default", "updated_at")
    list_filter = ("kind", "status", "payouts_enabled")
    search_fields = ("shop__name", "email", "external_id", "label")
    readonly_fields = ("shop", "kind", "external_id", "label", "email", "brand", "last4", "country", "currency", "status", "payouts_enabled", "created_at", "updated_at")
