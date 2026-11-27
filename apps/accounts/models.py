import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .profile_rules import validate_username

ROLE_ORDER = ["buyer", "seller", "moderator", "support", "admin", "superadmin"]


def avatar_upload_to(instance, filename):
    # Nom aléatoire : le nom de fichier fourni par l'utilisateur n'est jamais conservé (voir accounts/images.py).
    return f"profiles/avatars/{uuid.uuid4().hex}.webp"


def cover_upload_to(instance, filename):
    return f"profiles/covers/{uuid.uuid4().hex}.webp"


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

    # ----- Profil public (partageable : /u/<username>/) -----
    username = models.CharField(max_length=30, unique=True, null=True, blank=True, default=None, validators=[validate_username],
                                help_text="Identifiant public : indpns.com/u/<identifiant>")
    # Anciens champs fichier : OBSOLÈTES, conservés uniquement car leurs colonnes existent déjà en base (NOT NULL).
    # Les images sont désormais stockées en base, comme Mindus Forge : voir ProfileImage et avatar_version/cover_version.
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, editable=False)
    cover = models.ImageField(upload_to=cover_upload_to, blank=True, editable=False)
    # Version des images (horodatage en ms ; 0 = aucune). Sert d'URL versionnée (?v=…) : jamais de vieille image en cache.
    avatar_version = models.BigIntegerField(default=0, editable=False)
    cover_version = models.BigIntegerField(default=0, editable=False)
    cover_position_y = models.PositiveSmallIntegerField(default=50, editable=False)   # cadrage vertical de la couverture, 0–100 %
    headline = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=600, blank=True)
    location = models.CharField(max_length=80, blank=True)
    website = models.URLField(blank=True)
    github = models.CharField(max_length=39, blank=True)
    twitter = models.CharField(max_length=15, blank=True)
    linkedin = models.CharField(max_length=100, blank=True)
    profile_public = models.BooleanField(default=False)   # opt-in : rien n'est public tant que l'utilisateur ne l'a pas choisi
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

    @property
    def has_public_page(self):
        """Vrai si le lien public existe ET est ouvert à tous."""
        return bool(self.username and self.profile_public and self.is_active)

    def get_public_url(self):
        return reverse("profiles:detail", args=[self.username]) if self.username else ""

    @property
    def has_avatar(self):
        return bool(self.avatar_version)

    @property
    def has_cover(self):
        return bool(self.cover_version)

    @property
    def avatar_url(self):
        return f"{reverse('profiles:avatar', args=[self.pk])}?v={self.avatar_version}" if self.avatar_version else ""

    @property
    def cover_url(self):
        return f"{reverse('profiles:cover', args=[self.pk])}?v={self.cover_version}" if self.cover_version else ""

    @property
    def avatar_initial(self):
        return (self.get_short_name() or "?")[:1].upper()

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


class ProfileImage(models.Model):
    """Octets des images de profil (avatar + couverture), stockés EN BASE comme Mindus Forge : persistants sur Render sans S3.
    Table séparée de User pour ne jamais charger ces blobs à chaque requête authentifiée (chargés uniquement par la route de service)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="images")
    avatar_data = models.BinaryField(null=True, blank=True)
    avatar_mime = models.CharField(max_length=40, blank=True)
    cover_data = models.BinaryField(null=True, blank=True)
    cover_mime = models.CharField(max_length=40, blank=True)

    def __str__(self):
        return f"Images de {self.user_id}"
