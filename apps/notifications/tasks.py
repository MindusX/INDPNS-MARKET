from celery import shared_task

from .brevo import BrevoError
from .services import _deliver


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_email(self, to, subject, text, html):
    try:
        _deliver(to, subject, text, html)
    except BrevoError as exc:
        if not exc.retryable:   # 4xx (expéditeur non validé, adresse invalide…) : inutile de réessayer
            raise
        raise self.retry(exc=exc)
    except Exception as exc:
        raise self.retry(exc=exc)
