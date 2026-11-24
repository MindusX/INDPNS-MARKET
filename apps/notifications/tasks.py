from celery import shared_task

from .services import _deliver


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_email(self, to, subject, text, html):
    try:
        _deliver(to, subject, text, html)
    except Exception as exc:
        raise self.retry(exc=exc)
