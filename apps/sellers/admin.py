from django.contrib import admin

from .models import SellerPlan, Shop


@admin.register(SellerPlan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_monthly", "price_yearly", "commission_rate", "is_active", "sort_order")


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "plan", "verification_status", "kyc_status", "is_active")
    list_filter = ("plan", "verification_status", "kyc_status", "is_active")
    search_fields = ("name", "user__email")
