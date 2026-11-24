import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Notification

logger = logging.getLogger(__name__)


def notify(user, kind, title, body="", url=""):
    return Notification.objects.create(user=user, kind=kind, title=title[:160], body=body[:500], url=url[:300])


def _deliver(to, subject, text, html):
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to])
    msg.attach_alternative(html, "text/html")
    msg.send()


def send_email(to, subject, template, context=None):
    ctx = {"SITE_NAME": settings.SITE_NAME, "SITE_URL": settings.SITE_URL, "subject": subject}
    ctx.update(context or {})
    html = render_to_string(template, ctx)
    text = strip_tags(html)
    try:
        if settings.CELERY_ENABLED:
            from .tasks import deliver_email
            deliver_email.delay(to, subject, text, html)
        else:
            _deliver(to, subject, text, html)
    except Exception:
        logger.exception("email delivery failed (%s)", subject)
