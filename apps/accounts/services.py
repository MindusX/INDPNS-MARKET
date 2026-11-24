from django.conf import settings
from django.urls import reverse

from apps.notifications.services import send_email

from .tokens import make_verify_token


def send_verification_email(user, request=None):
    path = reverse("accounts:verify", args=[make_verify_token(user)])
    base = request.build_absolute_uri("/").rstrip("/") if request else settings.SITE_URL
    send_email(user.email, "Confirm your email · INDPNS Market", "emails/verify_email.html",
               {"user": user, "url": base + path})
