"""Formulaire de vérification d'identité : identité légale, adresse, pièce d'identité (recto/verso) et selfie."""
import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.core.countries import COUNTRIES

from .kyc_images import process_document_image
from .models import IdentityVerification

NAME_RE = re.compile(r"^[^\W\d_](?:[^\W\d_]|[ .'’-])*$", re.UNICODE)
PHONE_RE = re.compile(r"^\+?[0-9 ().\-]{6,25}$")
COUNTRY_CHOICES = [("", _("Select a country…"))] + COUNTRIES
FILE_ATTRS = {"accept": "image/jpeg,image/png,image/webp", "class": "sr-only"}


def _years_between(born, today):
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class IdentityForm(forms.Form):
    first_name = forms.CharField(label=_("Legal first name"), max_length=80)
    last_name = forms.CharField(label=_("Legal last name"), max_length=80)
    date_of_birth = forms.DateField(label=_("Date of birth"), widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                                    input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    nationality = forms.ChoiceField(label=_("Nationality"), choices=COUNTRY_CHOICES)
    address_line1 = forms.CharField(label=_("Address"), max_length=120)
    address_line2 = forms.CharField(label=_("Address line 2"), max_length=120, required=False)
    city = forms.CharField(label=_("City"), max_length=80)
    region = forms.CharField(label=_("State / region"), max_length=80, required=False)
    postal_code = forms.CharField(label=_("Postal code"), max_length=20, required=False)
    country = forms.ChoiceField(label=_("Country of residence"), choices=COUNTRY_CHOICES)
    phone = forms.CharField(label=_("Phone (optional)"), max_length=30, required=False, widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}))
    doc_type = forms.ChoiceField(label=_("Document type"), choices=IdentityVerification.DOC_TYPES)
    doc_country = forms.ChoiceField(label=_("Issuing country"), choices=COUNTRY_CHOICES)
    front = forms.FileField(label=_("Document — front"), required=False, widget=forms.FileInput(attrs={**FILE_ATTRS, "data-kyc-file": "front"}))
    back = forms.FileField(label=_("Document — back"), required=False, widget=forms.FileInput(attrs={**FILE_ATTRS, "data-kyc-file": "back"}))
    selfie = forms.FileField(label=_("Selfie holding your document"), required=False, widget=forms.FileInput(attrs={**FILE_ATTRS, "data-kyc-file": "selfie"}))
    consent = forms.BooleanField(label=_("I certify that this information is accurate and I consent to its processing to verify my identity."))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.images = {}
        for name in ("first_name", "last_name"):
            self.fields[name].widget.attrs["autocomplete"] = "given-name" if name == "first_name" else "family-name"

    def _name(self, field):
        v = " ".join((self.cleaned_data.get(field) or "").split())
        if not NAME_RE.match(v):
            raise ValidationError(_("Use letters only, exactly as written on your document."))
        return v

    def clean_first_name(self):
        return self._name("first_name")

    def clean_last_name(self):
        return self._name("last_name")

    def clean_date_of_birth(self):
        born = self.cleaned_data["date_of_birth"]
        age = _years_between(born, date.today())
        if age < 18:
            raise ValidationError(_("You must be at least 18 years old to receive payouts."))
        if age > 120:
            raise ValidationError(_("Please enter a valid date of birth."))
        return born

    def clean_phone(self):
        v = (self.cleaned_data.get("phone") or "").strip()
        if v and not PHONE_RE.match(v):
            raise ValidationError(_("Enter a valid phone number, e.g. +33 6 12 34 56 78."))
        return v

    def clean_postal_code(self):
        v = " ".join((self.cleaned_data.get("postal_code") or "").split())
        if v and not re.match(r"^[A-Za-z0-9][A-Za-z0-9 \-]{1,19}$", v):
            raise ValidationError(_("Enter a valid postal code."))
        return v

    def clean(self):
        data = super().clean()
        needs_back = data.get("doc_type") in ("national_id", "driver_license")
        for kind, required in (("front", True), ("back", needs_back), ("selfie", True)):
            f = self.files.get(kind)
            if not f:
                if required:
                    self.add_error(kind, _("This file is required."))
                continue
            try:
                self.images[kind] = process_document_image(f)
            except ValidationError as exc:
                self.add_error(kind, exc)
        return data

    def verification_data(self):
        keys = ("first_name", "last_name", "date_of_birth", "nationality", "address_line1", "address_line2", "city", "region",
                "postal_code", "country", "phone", "doc_type", "doc_country")
        return {k: self.cleaned_data[k] for k in keys}
