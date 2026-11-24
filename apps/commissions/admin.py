from django.contrib import admin

from .models import LedgerEntry


@admin.register(LedgerEntry)
class LedgerAdmin(admin.ModelAdmin):
    list_display = ("created_at", "entry_type", "shop", "amount", "currency", "idempotency_key")
    list_filter = ("entry_type",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
