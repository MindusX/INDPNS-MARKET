from decimal import Decimal

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Category, Technology
from apps.core.files import validate_image_file, validate_product_file
from apps.licenses.models import LicenseType, ProductLicensePrice

from .models import Product, ProductImage, ProductReport


class InfoForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["title", "summary", "category"]
        labels = {"title": _("Product name"), "summary": _("One-line summary"), "category": _("Category")}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["category"].required = True


class DescriptionForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["description", "documentation"]
        labels = {"description": _("Description"), "documentation": _("Documentation / installation notes")}
        widgets = {"description": forms.Textarea(attrs={"rows": 10}), "documentation": forms.Textarea(attrs={"rows": 8})}


class TechForm(forms.ModelForm):
    technologies = forms.ModelMultipleChoiceField(queryset=Technology.objects.all(), required=False, widget=forms.CheckboxSelectMultiple, label=_("Technologies"))

    class Meta:
        model = Product
        fields = ["technologies", "compatibility", "demo_url", "video_url"]
        labels = {"compatibility": _("Compatibility (e.g. Django 5, Python 3.12)"), "demo_url": _("Live demo URL"), "video_url": _("Video URL")}


class MediaForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["cover"]
        labels = {"cover": _("Cover image (JPG, PNG or WebP)")}

    def clean_cover(self):
        f = self.cleaned_data.get("cover")
        if isinstance(f, UploadedFile):
            validate_image_file(f)
        return f


class GalleryForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "caption"]

    def clean_image(self):
        f = self.cleaned_data["image"]
        validate_image_file(f)
        return f


class VersionForm(forms.Form):
    version = forms.CharField(max_length=30, label=_("Version"), initial="1.0.0")
    changelog = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False, label=_("What changed?"))
    file = forms.FileField(label=_("File (ZIP or PDF)"))

    def clean_file(self):
        f = self.cleaned_data["file"]
        validate_product_file(f)
        return f


class PricingForm(forms.Form):
    CODES = ["personal", "commercial", "extended"]
    personal = forms.DecimalField(min_value=Decimal("0"), max_value=Decimal("5000"), decimal_places=2, label=_("Personal license (USD, 0 = free)"))
    commercial = forms.DecimalField(min_value=Decimal("1"), max_value=Decimal("5000"), decimal_places=2, required=False, label=_("Commercial license (USD, optional)"))
    extended = forms.DecimalField(min_value=Decimal("1"), max_value=Decimal("5000"), decimal_places=2, required=False, label=_("Extended license (USD, optional)"))

    def __init__(self, *a, product=None, **kw):
        super().__init__(*a, **kw)
        self.product = product
        if product is not None and not self.is_bound:
            for lp in ProductLicensePrice.objects.filter(product=product).select_related("license_type"):
                self.fields[lp.license_type.code].initial = lp.price

    def clean_personal(self):
        v = self.cleaned_data["personal"]
        if v != 0 and v < Decimal("1"):
            raise forms.ValidationError(_("Paid products start at $1.00."))
        return v

    def save(self):
        types = {t.code: t for t in LicenseType.objects.filter(code__in=self.CODES)}
        for code in self.CODES:
            val = self.cleaned_data.get(code)
            lt = types.get(code)
            if lt is None:
                continue
            if val is None:
                ProductLicensePrice.objects.filter(product=self.product, license_type=lt).delete()
            else:
                ProductLicensePrice.objects.update_or_create(product=self.product, license_type=lt, defaults={"price": val})
        from .services import refresh_base_price
        refresh_base_price(self.product)


class ReportForm(forms.ModelForm):
    class Meta:
        model = ProductReport
        fields = ["reason", "details"]
