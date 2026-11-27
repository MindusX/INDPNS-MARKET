"""Moyens de réception des gains : connexion PayPal (OAuth) et carte / compte bancaire (Stripe Connect)."""
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.core.permissions import seller_required
from apps.core.ratelimit import ratelimit
from apps.core.services import audit
from apps.payouts import connect as pc
from apps.payouts.models import PayoutMethod

from .navigation import context

STATE_KEY = "paypal_oauth"
STATE_TTL = 600          # 10 minutes pour finir la connexion chez PayPal


def _absolute(name):
    return settings.SITE_URL + reverse(name)


def _methods(shop):
    by_kind = {m.kind: m for m in shop.payout_methods.all()}
    return by_kind.get("paypal"), by_kind.get("stripe")


@seller_required
@ratelimit("payout-methods", limit=40, window=600)
@require_http_methods(["GET", "POST"])
def seller_payout_methods(request):
    shop = request.user.shop
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "connect_paypal":
                if not pc.paypal_configured():
                    raise pc.ConnectError(_("PayPal connection is not available yet."))
                state = secrets.token_urlsafe(32)
                request.session[STATE_KEY] = {"state": state, "ts": int(time.time()), "shop": shop.pk}
                return redirect(pc.paypal_authorize_url(_absolute("dashboard:seller_paypal_callback"), state))
            if action == "connect_stripe":
                url = pc.stripe_start(shop, _absolute("dashboard:seller_stripe_return"), _absolute("dashboard:seller_stripe_refresh"))
                return redirect(url)
            if action == "refresh_stripe":
                method = get_object_or_404(PayoutMethod, shop=shop, kind="stripe")
                m = pc.stripe_sync(method)
                messages.success(request, _("Your bank card / account is connected.") if m.is_usable else _("Your account is not ready to receive payouts yet."))
            elif action in ("disconnect", "make_default"):
                method = get_object_or_404(PayoutMethod, pk=request.POST.get("method_id"), shop=shop)
                if action == "disconnect":
                    audit(request.user, "payout_method.disconnected", method, request, kind=method.kind)
                    pc.disconnect(method)
                    messages.success(request, _("Payout method disconnected."))
                else:
                    pc.set_default(shop, method)
                    messages.success(request, _("Default payout method updated."))
        except pc.ConnectError as e:
            messages.error(request, str(e))
        return redirect("dashboard:seller_payout_methods")

    paypal, stripe_m = _methods(shop)
    return render(request, "dashboard/seller/payout_methods.html", context(
        request, "seller", shop=shop, paypal=paypal, stripe_method=stripe_m,
        paypal_ready=pc.paypal_configured(), stripe_ready=pc.stripe_configured(), has_usable=any(m.is_usable for m in (paypal, stripe_m) if m)))


@seller_required
def seller_paypal_callback(request):
    """Retour de PayPal après autorisation. L'état (anti-CSRF) est vérifié avant tout échange de code."""
    saved = request.session.pop(STATE_KEY, None)
    given = request.GET.get("state", "")
    valid = bool(saved) and saved.get("shop") == request.user.shop.pk and time.time() - saved.get("ts", 0) <= STATE_TTL \
        and secrets.compare_digest(str(saved.get("state", "")).encode(), given.encode())
    if not valid:
        messages.error(request, _("The connection request expired or is invalid. Please try again."))
    elif request.GET.get("error"):
        messages.info(request, _("PayPal connection cancelled."))
    elif not request.GET.get("code"):
        messages.error(request, _("PayPal did not confirm the connection. Please try again."))
    else:
        try:
            method = pc.connect_paypal(request.user.shop, request.GET["code"])
            audit(request.user, "payout_method.connected", method, request, kind="paypal")
            messages.success(request, _("PayPal account connected."))
        except pc.ConnectError as e:
            messages.error(request, str(e))
    return redirect("dashboard:seller_payout_methods")


@seller_required
def seller_stripe_return(request):
    """Retour de l'onboarding Stripe : on relit l'état du compte côté serveur (on ne fait confiance à aucun paramètre d'URL)."""
    method = request.user.shop.payout_methods.filter(kind="stripe").first()
    if method is None:
        return redirect("dashboard:seller_payout_methods")
    try:
        m = pc.stripe_sync(method)
        if m.is_usable:
            audit(request.user, "payout_method.connected", m, request, kind="stripe")
            messages.success(request, _("Your bank card / account is connected."))
        else:
            messages.info(request, _("Setup is not finished yet. Complete the remaining steps to receive payouts."))
    except pc.ConnectError as e:
        messages.error(request, str(e))
    return redirect("dashboard:seller_payout_methods")


@seller_required
def seller_stripe_refresh(request):
    """Le lien d'onboarding Stripe a expiré : on en génère un nouveau."""
    try:
        return redirect(pc.stripe_start(request.user.shop, _absolute("dashboard:seller_stripe_return"), _absolute("dashboard:seller_stripe_refresh")))
    except pc.ConnectError as e:
        messages.error(request, str(e))
        return redirect("dashboard:seller_payout_methods")
