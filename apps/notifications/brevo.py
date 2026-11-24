"""Envoi d'e-mails via l'API HTTPS de Brevo (https://api.brevo.com/v3/smtp/email).

Aucune dépendance externe (bibliothèque standard uniquement) et aucune connexion SMTP : fonctionne sur
Render même lorsque les ports SMTP sortants sont bloqués.

Utilisation :
  * automatiquement, via Django (``send_mail``, ``EmailMultiAlternatives``, réinitialisation de mot de passe,
    ``apps.notifications.services.send_email``…) : ``EMAIL_BACKEND`` pointe sur ``BrevoEmailBackend``
    dès que ``BREVO_API_KEY`` est définie ;
  * directement : ``send_brevo_email(to, subject, html=..., text=...)``.

Variables d'environnement : ``BREVO_API_KEY`` (secret) et ``MAIL_FROM`` (expéditeur validé dans Brevo).
La clé n'est jamais journalisée ni insérée dans un message d'erreur.
"""
import base64
import json
import logging
import socket
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
DEFAULT_TIMEOUT = 15
_MAX_ERROR_CHARS = 300


class BrevoError(Exception):
    """Échec d'envoi Brevo. Le message ne contient jamais la clé API.

    ``status`` : code HTTP (None pour une erreur réseau/configuration).
    ``retryable`` : True si une nouvelle tentative a un sens (réseau, 429, 5xx).
    """

    def __init__(self, message, status=None, retryable=False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


# ---------- configuration ----------

def _api_key():
    return (getattr(settings, "BREVO_API_KEY", "") or "").strip()


def _redact(text, api_key):
    text = str(text or "")
    if api_key:
        text = text.replace(api_key, "[redacted]")
    return text[:_MAX_ERROR_CHARS]


def _sender_for(message=None):
    """MAIL_FROM en priorité, sinon DEFAULT_FROM_EMAIL (compatibilité), sinon l'expéditeur du message."""
    raw = (getattr(settings, "MAIL_FROM", "") or "").strip()
    if not raw and message is not None:
        raw = (message.from_email or "").strip()
    if not raw:
        raw = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    return _address(raw)


def _address(raw):
    """« Nom <a@b.c> » ou « a@b.c » -> {"email": ..., "name": ...} (name optionnel)."""
    name, email = parseaddr(str(raw or ""))
    email = (email or "").strip()
    if not email or "@" not in email:
        raise BrevoError("Invalid e-mail address in message or MAIL_FROM configuration.")
    out = {"email": email}
    if name.strip():
        out["name"] = name.strip()
    return out


def _addresses(values):
    return [_address(v) for v in (values or []) if str(v or "").strip()]


# ---------- construction du message ----------

def build_payload(message):
    """Transforme un ``EmailMessage`` Django en corps JSON pour l'API Brevo."""
    to = _addresses(message.to)
    if not to:
        raise BrevoError("Message has no recipient.")
    payload = {"sender": _sender_for(message), "to": to, "subject": message.subject or "(no subject)"}
    cc, bcc, reply_to = _addresses(message.cc), _addresses(message.bcc), _addresses(message.reply_to)
    if cc:
        payload["cc"] = cc
    if bcc:
        payload["bcc"] = bcc
    if reply_to:
        payload["replyTo"] = reply_to[0]   # Brevo n'accepte qu'une adresse de réponse

    html, text = None, None
    body = message.body or ""
    if getattr(message, "content_subtype", "plain") == "html":
        html = body
    else:
        text = body
    for content, mimetype in getattr(message, "alternatives", []) or []:
        if mimetype == "text/html":
            html = content
    if html:
        payload["htmlContent"] = html
    if text:
        payload["textContent"] = text
    if not html and not text:
        raise BrevoError("Message has no content.")

    attachments = []
    for att in getattr(message, "attachments", []) or []:
        if isinstance(att, tuple) and len(att) >= 2:
            filename, content = att[0], att[1]
            data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
            attachments.append({"name": filename or "attachment", "content": base64.b64encode(data).decode("ascii")})
    if attachments:
        payload["attachment"] = attachments

    extra = {k: str(v) for k, v in (message.extra_headers or {}).items() if k.lower() not in ("from", "to", "cc", "bcc", "subject", "reply-to")}
    if extra:
        payload["headers"] = extra
    return payload


# ---------- appel HTTP ----------

def post_to_brevo(payload, api_key=None, timeout=None):
    """POST du payload sur l'API Brevo. Retourne le JSON de réponse (``{"messageId": ...}``) ou lève BrevoError."""
    api_key = (api_key if api_key is not None else _api_key())
    if not api_key:
        raise BrevoError("BREVO_API_KEY is not configured.")
    timeout = timeout or getattr(settings, "BREVO_TIMEOUT", DEFAULT_TIMEOUT)
    url = getattr(settings, "BREVO_API_URL", "") or BREVO_API_URL
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"api-key": api_key, "accept": "application/json", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - URL fixe en HTTPS
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            data = json.loads(exc.read().decode("utf-8", "replace"))
            detail = " (%s) %s" % (data.get("code", ""), data.get("message", ""))
        except Exception:  # corps vide ou non JSON
            pass
        raise BrevoError(_redact("Brevo API error %s%s" % (exc.code, detail), api_key), status=exc.code,
                         retryable=(exc.code == 429 or exc.code >= 500)) from None
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise BrevoError("Brevo network error: %s" % type(reason).__name__, retryable=True) from None

    if not 200 <= status < 300:
        raise BrevoError("Brevo API unexpected status %s" % status, status=status, retryable=status >= 500)
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        return {}


def send_brevo_email(to, subject, html="", text="", reply_to=None):
    """Envoi direct (hors backend Django). ``to`` : adresse ou liste. Retourne le messageId Brevo."""
    from django.core.mail import EmailMultiAlternatives
    recipients = [to] if isinstance(to, str) else list(to)
    msg = EmailMultiAlternatives(subject, text or "", None, recipients, reply_to=[reply_to] if reply_to else None)
    if html:
        msg.attach_alternative(html, "text/html")
    return post_to_brevo(build_payload(msg)).get("messageId")


# ---------- backend Django ----------

class BrevoEmailBackend(BaseEmailBackend):
    """Backend Django : ``EMAIL_BACKEND = "apps.notifications.brevo.BrevoEmailBackend"``.

    ``send_messages`` retourne le nombre d'e-mails acceptés par Brevo. En cas d'échec, ``BrevoError`` est levée
    (sauf ``fail_silently=True``) afin que l'appelant, ou la tâche Celery, puisse réagir.
    """

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            try:
                result = post_to_brevo(build_payload(message))
            except BrevoError as exc:
                logger.error("Brevo send failed: %s", exc)
                if not self.fail_silently:
                    raise
                continue
            sent += 1
            logger.info("Brevo email accepted (messageId=%s)", result.get("messageId", "?"))
        return sent
