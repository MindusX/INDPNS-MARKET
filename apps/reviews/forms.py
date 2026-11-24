from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(choices=[(i, str(i)) for i in range(5, 0, -1)], coerce=int, label=_("Rating"))

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        labels = {"comment": _("Your review")}
        widgets = {"comment": forms.Textarea(attrs={"rows": 4})}
