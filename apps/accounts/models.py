from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

ROLE_ORDER = ["buyer", "seller", "moderator", "support", "admin", "superadmin"]


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role="superadmin", email_verified=True)
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [(r, r.capitalize()) for r in ROLE_ORDER]
    THEME_CHOICES = [("light", "Light"), ("dark", "Dark")]

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=80)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="buyer", db_index=True)
    email_verified = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=5, default="en")
    theme = models.CharField(max_length=8, choices=THEME_CHOICES, default="light")
    totp_enabled = models.BooleanField(default=False)   # 2FA TOTP : champ réservé (non implémenté)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    def get_short_name(self):
        return self.display_name or self.email.split("@")[0]

    def has_role_at_least(self, role):
        if self.is_superuser:
            return True
        return ROLE_ORDER.index(self.role) >= ROLE_ORDER.index(role)

    @property
    def is_seller(self):
        return hasattr(self, "shop")

    @property
    def is_moderator(self):
        return self.has_role_at_least("moderator")

    @property
    def is_internal(self):
        return self.has_role_at_least("moderator")


class LoginEvent(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="login_events")
    email = models.CharField(max_length=254, blank=True)
    success = models.BooleanField()
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions_tracked")
    session_key = models.CharField(max_length=40, unique=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
