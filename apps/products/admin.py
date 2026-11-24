from django.contrib import admin

from .models import Product, ProductImage, ProductReport, ProductVersion


class VersionInline(admin.TabularInline):
    model = ProductVersion
    extra = 0
    readonly_fields = ("sha256", "file_size", "scan_status")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "shop", "status", "base_price", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "shop__name")
    inlines = [VersionInline]


admin.site.register(ProductImage)
admin.site.register(ProductReport)
