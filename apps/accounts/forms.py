from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from urllib.parse import urlparse

from .models import User
from .profile_rules import (GITHUB_RE, LINKEDIN_RE, TWITTER_RE, USERNAME_MAX, USERNAME_MIN, clean_handle,
                            normalize_username, validate_username)

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
    """Profil avancé : identité publique, liens et visibilité.
    Les images (avatar + couverture) ne passent PAS par ce formulaire : comme Mindus Forge, elles sont envoyées en AJAX
    (apps/accounts/profile_api.py), stockées en base et affichées immédiatement."""
    website = forms.URLField(required=False, assume_scheme="https", label=_("Website"),
                             widget=forms.URLInput(attrs={"placeholder": "https://example.com"}))

    class Meta:
        model = User
        fields = ["display_name", "username", "headline", "bio", "location", "website",
                  "github", "twitter", "linkedin", "profile_public", "preferred_language", "marketing_consent"]
        labels = {
            "display_name": _("Display name"), "username": _("Username"), "headline": _("Headline"), "bio": _("About you"),
            "location": _("Location"), "github": _("GitHub"), "twitter": _("X (Twitter)"), "linkedin": _("LinkedIn"),
            "profile_public": _("Make my profile public"), "preferred_language": _("Language"),
            "marketing_consent": _("I agree to receive product news (optional)"),
        }
        help_texts = {
            "username": _("Your public link: 3–30 characters, lowercase letters, numbers, - or _. Changing it breaks links you already shared."),
            "headline": _("A short line under your name, e.g. “Full-stack developer & UI designer”."),
            "bio": _("Tell visitors who you are and what you build. Plain text, up to 600 characters."),
            "location": _("City or country (optional)."),
            "github": _("Username or profile URL."), "twitter": _("Username or profile URL."), "linkedin": _("Username or profile URL."),
        }
        widgets = {
            "preferred_language": forms.Select(choices=[("en", "English"), ("fr", "Français"), ("es", "Español")]),
            "bio": forms.Textarea(attrs={"rows": 5, "maxlength": 600, "data-pf-bio": ""}),
            "headline": forms.TextInput(attrs={"maxlength": 100, "placeholder": _("What you do, in one line")}),
            "username": forms.TextInput(attrs={"maxlength": USERNAME_MAX, "minlength": USERNAME_MIN, "autocomplete": "off", "autocapitalize": "none",
                                               "spellcheck": "false", "placeholder": "your-name", "data-pf-username": ""}),
            "location": forms.TextInput(attrs={"maxlength": 80, "placeholder": _("Paris, France")}),
            "github": forms.TextInput(attrs={"placeholder": "octocat", "autocapitalize": "none"}),
            "twitter": forms.TextInput(attrs={"placeholder": "username", "autocapitalize": "none"}),
            "linkedin": forms.TextInput(attrs={"placeholder": "your-name", "autocapitalize": "none"}),
        }

    # ---- identité ----
    def clean_display_name(self):
        name = " ".join((self.cleaned_data.get("display_name") or "").split())
        if len(name) < 2:
            raise forms.ValidationError(_("Please enter at least 2 characters."))
        return name

    def clean_username(self):
        value = normalize_username(self.cleaned_data.get("username"))
        if not value:
            return None
        validate_username(value)
        if User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("This username is already taken."))
        return value

    def clean_headline(self):
        return " ".join((self.cleaned_data.get("headline") or "").split())

    def clean_bio(self):
        # texte brut : les sauts de ligne sont conservés ; le HTML n'est jamais interprété (échappement à l'affichage)
        bio = (self.cleaned_data.get("bio") or "").replace("\r\n", "\n").strip()
        return "\n".join(line.rstrip() for line in bio.split("\n"))

    def clean_location(self):
        return " ".join((self.cleaned_data.get("location") or "").split())

    # ---- liens ----
    def clean_website(self):
        url = (self.cleaned_data.get("website") or "").strip()
        if url and urlparse(url).scheme not in ("http", "https"):
            raise forms.ValidationError(_("Only http:// and https:// links are allowed."))
        return url

    def _handle(self, field, regex, hosts):
        value = clean_handle(self.cleaned_data.get(field), hosts)
        if value and not regex.match(value):
            raise forms.ValidationError(_("This username does not look valid."))
        return value

    def clean_github(self):
        return self._handle("github", GITHUB_RE, ("github.com",))

    def clean_twitter(self):
        return self._handle("twitter", TWITTER_RE, ("x.com", "twitter.com", "mobile.twitter.com"))

    def clean_linkedin(self):
        return self._handle("linkedin", LINKEDIN_RE, ("linkedin.com", "fr.linkedin.com", "uk.linkedin.com"))

    def clean(self):
        data = super().clean()
        if data.get("profile_public") and "username" not in self.errors and not data.get("username"):
            self.add_error("username", _("Choose a username to make your profile public."))
        return data
