from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        labels = {"name": _("Your name"), "email": _("Email"), "subject": _("Subject"), "message": _("Message")}
        widgets = {"message": forms.Textarea(attrs={"rows": 6})}
