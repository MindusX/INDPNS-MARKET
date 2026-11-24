from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from .models import User

MAX_FAILS = 5
LOCK_SECONDS = 15 * 60


class RegisterForm(forms.Form):
    display_name = forms.CharField(label=_("Your name"), max_length=80)
    email = forms.EmailField(label=_("Email"))
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label=_("Confirm password"), widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    accept_terms = forms.BooleanField(label=_("I accept the Terms of Service and the Privacy Policy"))
    marketing_consent = forms.BooleanField(required=False, label=_("I agree to receive product news (optional)"))

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", _("Passwords do not match."))
        elif p1:
            temp = User(email=data.get("email", ""), display_name=data.get("display_name", ""))
            try:
                password_validation.validate_password(p1, temp)
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return data

    def save(self):
        d = self.cleaned_data
        return User.objects.create_user(d["email"], d["password1"], display_name=d["display_name"],
                                        marketing_consent=d.get("marketing_consent", False))


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label=_("Email"), widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))

    def _key(self):
        return "loginfail:" + (self.data.get("username", "").lower().strip())

    def clean(self):
        key = self._key()
        if (cache.get(key) or 0) >= MAX_FAILS:
            raise forms.ValidationError(_("Too many failed attempts. Try again in 15 minutes or reset your password."), code="locked")
        try:
            data = super().clean()
        except forms.ValidationError:
            cache.add(key, 0, LOCK_SECONDS)
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, LOCK_SECONDS)
            raise
        cache.delete(key)
        return data

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        from django.conf import settings
        if settings.EMAIL_VERIFICATION_REQUIRED and not user.email_verified:
            self.unverified_user = user
            raise forms.ValidationError(_("Please confirm your email address first. Check your inbox."), code="unverified")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["display_name", "preferred_language", "marketing_consent"]
        widgets = {"preferred_language": forms.Select(choices=[("en", "English"), ("fr", "Français"), ("es", "Español")])}
