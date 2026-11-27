from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LoginEvent, User, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "display_name", "username", "profile_public", "role", "email_verified", "is_active", "date_joined")
    list_filter = ("role", "email_verified", "is_active", "profile_public")
    search_fields = ("email", "display_name", "username")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "preferred_language", "theme", "marketing_consent")}),
        ("Public profile", {"fields": ("username", "profile_public", "avatar", "cover", "headline", "bio", "location", "website", "github", "twitter", "linkedin")}),
        ("Access", {"fields": ("role", "email_verified", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "display_name", "password1", "password2")}),)
    readonly_fields = ("avatar_version", "cover_version", "last_login", "date_joined")
    actions = ["remove_profile_images"]

    @admin.action(description="Supprimer les photos de profil et de couverture (modération)")
    def remove_profile_images(self, request, queryset):
        from .profile_images import remove_image
        for user in queryset:
            remove_image(user, "avatar")
            remove_image(user, "cover")
        self.message_user(request, f"Images supprimées pour {queryset.count()} utilisateur(s).", messages.SUCCESS)


admin.site.register(LoginEvent)
admin.site.register(UserSession)
