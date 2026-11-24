from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from apps.core.utils import client_ip

from .models import LoginEvent, UserSession


@receiver(user_logged_in)
def on_login(sender, request, user, **kw):
    if request is None:
        return
    ua = request.META.get("HTTP_USER_AGENT", "")[:300]
    LoginEvent.objects.create(user=user, email=user.email, success=True, ip=client_ip(request), user_agent=ua)
    if not request.session.session_key:
        request.session.save()
    UserSession.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={"user": user, "ip": client_ip(request), "user_agent": ua},
    )


@receiver(user_login_failed)
def on_fail(sender, credentials, request=None, **kw):
    if request is None:
        return
    LoginEvent.objects.create(email=str(credentials.get("username") or credentials.get("email") or "")[:254], success=False,
                              ip=client_ip(request), user_agent=request.META.get("HTTP_USER_AGENT", "")[:300])
