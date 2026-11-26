from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("u/<slug:username>/", views.public_profile, name="detail"),
]
