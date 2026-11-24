import logging

from .models import AuditLog
from .utils import client_ip

logger = logging.getLogger(__name__)


def audit(actor, action, target=None, request=None, **metadata):
    """Écrit une entrée d'audit. Ne doit jamais casser le flux appelant."""
    try:
        AuditLog.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            action=action,
            target_type=target.__class__.__name__ if target is not None else "",
            target_id=str(getattr(target, "pk", "")) if target is not None else "",
            metadata={k: str(v) for k, v in metadata.items()},
            ip=client_ip(request) if request else None,
        )
    except Exception:  # pragma: no cover
        logger.exception("audit failed for %s", action)
