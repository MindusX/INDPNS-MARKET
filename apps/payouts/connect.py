"""Connexion des comptes de réception des gains — par REDIRECTION, comme « Continuer avec Facebook » :

  PayPal : « Log in with PayPal » (OAuth 2.0 / OpenID Connect). Le vendeur s'authentifie chez PayPal, autorise notre application,
           revient avec un `code` que l'on échange côté serveur contre son identifiant PayPal et son e-mail confirmé.
  Carte / banque : Stripe Connect (Express). Stripe héberge la saisie de la carte bancaire ou du compte bancaire (et sa propre
           vérification) ; nous ne recevons que l'identifiant du compte Stripe et les 4 derniers chiffres.

Aucun mot de passe, numéro de carte ou IBAN ne transite par nos serveurs. Les secrets ne sont jamais écrits dans les journaux."""
import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

try:                                    # `stripe` figure dans requirements.txt ; import tolérant pour que le site démarre sans lui
    import stripe
except ImportError:                     # pragma: no cover
    stripe = None

from .models import PayoutMethod

logger = logging.getLogger(__name__)
PAYPAL_SCOPE = "openid email https://uri.paypal.com/services/paypalattributes"


class ConnectError(Exception):
    """Message sûr, affichable tel quel à l'utilisateur."""


# ------------------------------------------------------------------ HTTP minimal (urllib, délai d'attente, pas de secret en log)
def _http(method, url, *, data=None, headers=None, form=False, timeout=15):
    hdrs = {"Accept": "application/json", **(headers or {})}
    body = None
    if data is not None:
        if form:
            body, hdrs["Content-Type"] = urllib.parse.urlencode(data).encode(), "application/x-www-form-urlencoded"
        else:
            body, hdrs["Content-Type"] = json.dumps(data).encode(), "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:          # noqa: S310 - URL fixée par ce module (https)
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        logger.warning("Provider HTTP %s on %s %s", exc.code, method, urllib.parse.urlsplit(url).path)
        raise ConnectError(_("The provider refused the request. Please try again."))
    except (urllib.error.URLError, TimeoutError, OSError):
        logger.warning("Provider unreachable: %s", urllib.parse.urlsplit(url).netloc)
        raise ConnectError(_("Could not reach the provider. Please try again in a moment."))
    try:
        return json.loads(raw or b"{}")
    except ValueError:
        raise ConnectError(_("Unexpected response from the provider."))


# ------------------------------------------------------------------ PayPal (Log in with PayPal)
def paypal_configured():
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


def _paypal_hosts():
    if settings.PAYPAL_SANDBOX:
        return "https://www.sandbox.paypal.com", "https://api-m.sandbox.paypal.com"
    return "https://www.paypal.com", "https://api-m.paypal.com"


def paypal_authorize_url(redirect_uri, state):
    web, _api_host = _paypal_hosts()
    q = urllib.parse.urlencode({"flowEntry": "static", "client_id": settings.PAYPAL_CLIENT_ID, "response_type": "code",
                                "scope": PAYPAL_SCOPE, "redirect_uri": redirect_uri, "state": state})
    return f"{web}/signin/authorize?{q}"


def paypal_fetch_identity(code):
    """Échange le `code` OAuth puis lit le profil PayPal. Retourne {"payer_id", "email", "name"}."""
    _web_host, api = _paypal_hosts()
    basic = base64.b64encode(f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}".encode()).decode()
    token = _http("POST", f"{api}/v1/oauth2/token", data={"grant_type": "authorization_code", "code": code}, form=True,
                  headers={"Authorization": f"Basic {basic}"})
    access = token.get("access_token")
    if not access:
        raise ConnectError(_("PayPal did not confirm the connection. Please try again."))
    info = _http("GET", f"{api}/v1/identity/oauth2/userinfo?schema=paypalv1.1", headers={"Authorization": f"Bearer {access}"})
    emails = info.get("emails") or []
    primary = next((e for e in emails if e.get("primary")), emails[0] if emails else {})
    email = (primary.get("value") or info.get("email") or "").strip().lower()
    confirmed = bool(primary.get("confirmed", info.get("email_verified", False)))
    payer_id = (info.get("payer_id") or "").strip()
    if not payer_id or not email:
        raise ConnectError(_("PayPal did not return your account details. Please try again."))
    if not confirmed:
        raise ConnectError(_("Your PayPal email address is not confirmed. Confirm it on PayPal, then connect again."))
    return {"payer_id": payer_id, "email": email, "name": (info.get("name") or "").strip()}


def _mask_email(email):
    name, _at, domain = email.partition("@")
    return (name[:2] + "•••" if len(name) > 2 else name[:1] + "•••") + "@" + domain


def _promote_default(shop):
    if shop.payout_methods.filter(is_default=True).exists():
        return
    first = shop.payout_methods.filter(status="connected", payouts_enabled=True).first() or shop.payout_methods.first()
    if first:
        PayoutMethod.objects.filter(pk=first.pk).update(is_default=True)


def connect_paypal(shop, code):
    ident = paypal_fetch_identity(code)
    try:
        with transaction.atomic():
            taken = PayoutMethod.objects.filter(kind="paypal", external_id=ident["payer_id"]).exclude(shop=shop).exists()
            if taken:
                raise ConnectError(_("This PayPal account is already connected to another shop."))
            method, _new = PayoutMethod.objects.update_or_create(
                shop=shop, kind="paypal",
                defaults={"external_id": ident["payer_id"], "email": ident["email"], "label": f"PayPal · {_mask_email(ident['email'])}",
                          "status": "connected", "payouts_enabled": True})
            _promote_default(shop)
    except IntegrityError:
        raise ConnectError(_("This PayPal account is already connected to another shop."))
    return method


# ------------------------------------------------------------------ Stripe Connect (carte bancaire / compte bancaire)
def stripe_configured():
    return bool(settings.STRIPE_SECRET_KEY) and stripe is not None


def _stripe():
    if not stripe_configured():
        raise ConnectError(_("Bank card connection is not available yet."))
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def stripe_start(shop, return_url, refresh_url):
    """Crée (une seule fois) le compte Express du vendeur puis renvoie l'URL d'onboarding hébergée par Stripe."""
    st = _stripe()
    try:
        method = shop.payout_methods.filter(kind="stripe").first()
        if method is None:
            params = {"type": "express", "email": shop.user.email, "business_type": "individual",
                      "capabilities": {"transfers": {"requested": True}}, "metadata": {"shop_id": str(shop.pk)}}
            if len(shop.country or "") == 2:
                params["country"] = shop.country.upper()
            acct = st.Account.create(**params)
            method = PayoutMethod.objects.create(shop=shop, kind="stripe", external_id=acct["id"],
                                                 label=_("Bank card / account (setup in progress)"), status="pending")
        link = st.AccountLink.create(account=method.external_id, refresh_url=refresh_url, return_url=return_url, type="account_onboarding")
        return link["url"]
    except ConnectError:
        raise
    except Exception:                                    # noqa: BLE001 - erreurs Stripe : message sûr, détail dans les journaux
        logger.exception("Stripe onboarding failed for shop %s", shop.pk)
        raise ConnectError(_("We could not start the secure setup with our payment provider. Please try again."))


def stripe_sync(method):
    """Relit le compte Stripe et met à jour l'état + la carte/banque (marque, 4 derniers chiffres)."""
    st = _stripe()
    try:
        acct = st.Account.retrieve(method.external_id)
    except Exception:                                    # noqa: BLE001
        logger.exception("Stripe retrieve failed for %s", method.pk)
        raise ConnectError(_("We could not read your account status. Please try again."))
    enabled, submitted = bool(acct.get("payouts_enabled")), bool(acct.get("details_submitted"))
    data = ((acct.get("external_accounts") or {}).get("data")) or []
    ext = data[0] if data else {}
    brand = (ext.get("brand") or ext.get("bank_name") or "")[:40]
    last4 = (ext.get("last4") or "")[:4]
    if ext:
        kind_txt = _("card") if ext.get("object") == "card" else _("bank")
        method.label = f"{brand or kind_txt.capitalize()} •••• {last4}".strip() if last4 else (brand or _("Bank card / account"))
        method.brand, method.last4 = brand, last4
        method.country, method.currency = (ext.get("country") or "")[:2], (ext.get("currency") or "")[:3].upper()
    method.payouts_enabled = enabled
    method.status = "connected" if enabled else ("restricted" if submitted else "pending")
    method.save()
    _promote_default(method.shop)
    return method


def set_default(shop, method):
    with transaction.atomic():
        shop.payout_methods.update(is_default=False)
        PayoutMethod.objects.filter(pk=method.pk, shop=shop).update(is_default=True)


def disconnect(method):
    shop, was_default, kind, ext_id = method.shop, method.is_default, method.kind, method.external_id
    method.delete()
    if kind == "stripe" and stripe_configured():          # on libère le compte Express (refusé par Stripe s'il porte un solde : sans gravité)
        try:
            _stripe().Account.delete(ext_id)
        except Exception:                                  # noqa: BLE001
            logger.info("Stripe account %s could not be deleted (kept)", ext_id)
    if was_default:
        _promote_default(shop)
