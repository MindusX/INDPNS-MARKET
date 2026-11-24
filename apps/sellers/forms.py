from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from apps.core.files import validate_image_file

from .models import Shop


class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ["name", "description", "country", "website"]
        labels = {"name": _("Shop name"), "description": _("About your shop"), "country": _("Country (ISO code, e.g. FR)"), "website": _("Website")}
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_country(self):
        c = self.cleaned_data.get("country", "").upper().strip()
        if c and len(c) != 2:
            raise forms.ValidationError(_("Use a 2-letter country code."))
        return c


class ShopLogoForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ["logo"]

    def clean_logo(self):
        f = self.cleaned_data.get("logo")
        if isinstance(f, UploadedFile):
            validate_image_file(f)
        return f
