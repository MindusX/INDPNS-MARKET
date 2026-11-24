import logging

from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import WebhookEvent
from .providers.base import SignatureError
from .registry import get_provider
from .services import process_webhook

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def webhook(request, provider):
    p = get_provider()
    if p is None or p.name != provider or not p.is_configured():
        return HttpResponse(status=404)
    try:
        result = p.parse_webhook(request.body, request.headers)   # vérifie la signature
    except SignatureError:
        return HttpResponse(status=400)
    ev, created = WebhookEvent.objects.get_or_create(provider=provider, event_id=result.event_id, defaults={"event_type": result.event_type})
    if not created and ev.processed:
        return HttpResponse(status=200)
    try:
        with transaction.atomic():
            process_webhook(result)
        ev.processed, ev.error = True, ""
        ev.save(update_fields=["processed", "error"])
    except Exception as exc:
        logger.exception("webhook processing failed")
        ev.error = str(exc)[:500]
        ev.save(update_fields=["error"])
        return HttpResponse(status=500)   # le prestataire réessaiera
    return HttpResponse(status=200)
