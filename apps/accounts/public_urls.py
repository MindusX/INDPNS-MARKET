from django.urls import path

from . import profile_api, views

app_name = "profiles"

urlpatterns = [
    path("u/<slug:username>/", views.public_profile, name="detail"),
    # Images de profil — mêmes routes que Mindus Forge
    path("api/profile/avatar/<int:user_id>", profile_api.avatar_image, name="avatar"),
    path("api/profile/cover/<int:user_id>", profile_api.cover_image, name="cover"),
    path("api/profile/upload-avatar", profile_api.upload_avatar, name="upload_avatar"),
    path("api/profile/upload-cover", profile_api.upload_cover, name="upload_cover"),
    path("api/profile/avatar", profile_api.delete_avatar, name="delete_avatar"),
    path("api/profile/cover", profile_api.delete_cover, name="delete_cover"),
    path("api/profile/cover/position", profile_api.cover_position, name="cover_position"),
]
