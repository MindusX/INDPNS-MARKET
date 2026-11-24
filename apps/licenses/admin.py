from django.contrib import admin

from .models import License, LicenseType, ProductLicensePrice

admin.site.register(LicenseType)
admin.site.register(ProductLicensePrice)


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ("key", "buyer", "product", "license_type", "issued_at", "revoked_at")
    search_fields = ("key", "buyer__email", "product__title")
