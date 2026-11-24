from django.contrib import admin

from .models import DownloadLog, Invoice, Order, OrderItem


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = [f.name for f in OrderItem._meta.fields]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "buyer", "status", "total", "provider", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("number", "buyer__email")
    inlines = [ItemInline]
    readonly_fields = ("number", "buyer", "total", "subtotal", "provider", "provider_ref", "idempotency_key", "paid_at")


admin.site.register(Invoice)
admin.site.register(DownloadLog)
