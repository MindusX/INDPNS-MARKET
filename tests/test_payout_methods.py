"""Moyens de réception des gains : connexion PayPal (OAuth, « Log in with PayPal ») et carte / banque (Stripe Connect).
Tous les appels réseau sont simulés : aucun vrai appel à PayPal ou Stripe."""
from decimal import Decimal
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import AuditLog
from apps.payouts.connect import ConnectError
from apps.payouts.models import Payout, PayoutMethod
from apps.payouts.services import PayoutError, request_payout

from .conftest_helpers import make_seller, make_user, seed

PAYPAL = dict(PAYPAL_CLIENT_ID="cid-123", PAYPAL_CLIENT_SECRET="secret-xyz", PAYPAL_SANDBOX=False, SITE_URL="https://market.test")
PAYPAL_PROFILE = {"payer_id": "PAYER123", "name": "Jean Dupont", "emails": [{"value": "jean.dupont@example.com", "primary": True, "confirmed": True}]}


def paypal_http(profile=None):
    """Remplace connect._http : 1er appel = échange du code, 2e = profil PayPal."""
    return mock.patch("apps.payouts.connect._http", side_effect=[{"access_token": "tok"}, profile or PAYPAL_PROFILE])


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.user = make_seller("seller@example.com")
        self.shop = self.user.shop
        self.client.force_login(self.user)
        self.url = reverse("dashboard:seller_payout_methods")

    def start_paypal(self):
        r = self.client.post(self.url, {"action": "connect_paypal"})
        return r, self.client.session.get("paypal_oauth", {}).get("state", "")

    def callback(self, **params):
        return self.client.get(reverse("dashboard:seller_paypal_callback"), params)


@override_settings(**PAYPAL)
class PayPalConnectTests(Base):
    def test_requires_login_and_seller(self):
        anon = self.client_class()
        self.assertEqual(anon.get(self.url).status_code, 302)
        buyer = self.client_class()
        buyer.force_login(make_user("buyer@example.com"))
        self.assertEqual(buyer.get(self.url).status_code, 302)          # pas de boutique -> devenir vendeur

    def test_page_renders_with_both_providers(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Connect with PayPal")
        self.assertContains(r, "Connect a card or bank account")

    def test_connect_redirects_to_paypal_authorize_with_state(self):
        r, state = self.start_paypal()
        self.assertEqual(r.status_code, 302)
        loc = urlsplit(r["Location"])
        self.assertEqual(f"{loc.scheme}://{loc.netloc}{loc.path}", "https://www.paypal.com/signin/authorize")
        q = parse_qs(loc.query)
        self.assertEqual(q["client_id"], ["cid-123"])
        self.assertEqual(q["response_type"], ["code"])
        self.assertEqual(q["redirect_uri"], ["https://market.test/dashboard/seller/payout-methods/paypal/callback/"])
        self.assertEqual(q["state"], [state])
        self.assertGreaterEqual(len(state), 30)
        self.assertNotIn("secret-xyz", r["Location"])                   # le secret n'est jamais envoyé au navigateur

    @override_settings(PAYPAL_SANDBOX=True)
    def test_sandbox_uses_sandbox_host(self):
        r, _ = self.start_paypal()
        self.assertTrue(r["Location"].startswith("https://www.sandbox.paypal.com/signin/authorize"))

    @override_settings(PAYPAL_CLIENT_ID="", PAYPAL_CLIENT_SECRET="")
    def test_not_configured_is_disabled_and_refused(self):
        page = self.client.get(self.url)
        self.assertContains(page, "Not available yet")
        r = self.client.post(self.url, {"action": "connect_paypal"})
        self.assertRedirects(r, self.url)
        self.assertFalse(PayoutMethod.objects.exists())

    def test_callback_connects_account(self):
        _r, state = self.start_paypal()
        with paypal_http() as http:
            r = self.callback(code="AUTHCODE", state=state)
        self.assertRedirects(r, self.url)
        m = PayoutMethod.objects.get()
        self.assertEqual((m.shop, m.kind, m.external_id, m.email), (self.shop, "paypal", "PAYER123", "jean.dupont@example.com"))
        self.assertTrue(m.is_usable and m.is_default)
        self.assertIn("je•••@example.com", m.label)                    # l'e-mail est masqué dans le libellé
        token_call = http.call_args_list[0]
        self.assertEqual(token_call.args[:2], ("POST", "https://api-m.paypal.com/v1/oauth2/token"))
        self.assertEqual(token_call.kwargs["data"], {"grant_type": "authorization_code", "code": "AUTHCODE"})
        self.assertTrue(token_call.kwargs["headers"]["Authorization"].startswith("Basic "))
        self.assertTrue(AuditLog.objects.filter(action="payout_method.connected", actor=self.user).exists())

    def test_callback_rejects_wrong_missing_or_replayed_state(self):
        _r, state = self.start_paypal()
        with mock.patch("apps.payouts.connect._http") as http:
            self.callback(code="X", state="forged-state")               # mauvais état
            self.assertFalse(PayoutMethod.objects.exists())
            self.callback(code="X", state=state)                        # l'état a été consommé par la tentative précédente
            self.callback(code="X")                                     # pas d'état
            http.assert_not_called()                                    # aucun échange de code n'a eu lieu
        self.assertFalse(PayoutMethod.objects.exists())

    def test_callback_rejects_expired_state(self):
        _r, state = self.start_paypal()
        s = self.client.session
        s["paypal_oauth"]["ts"] -= 3600
        s.save()
        with mock.patch("apps.payouts.connect._http") as http:
            self.callback(code="X", state=state)
            http.assert_not_called()
        self.assertFalse(PayoutMethod.objects.exists())

    def test_user_cancel_is_handled(self):
        _r, state = self.start_paypal()
        with mock.patch("apps.payouts.connect._http") as http:
            r = self.callback(error="access_denied", state=state)
            http.assert_not_called()
        self.assertRedirects(r, self.url)
        self.assertFalse(PayoutMethod.objects.exists())

    def test_unconfirmed_paypal_email_is_refused(self):
        _r, state = self.start_paypal()
        bad = {**PAYPAL_PROFILE, "emails": [{"value": "x@example.com", "primary": True, "confirmed": False}]}
        with paypal_http(bad):
            self.callback(code="C", state=state)
        self.assertFalse(PayoutMethod.objects.exists())

    def test_provider_failure_shows_safe_error(self):
        _r, state = self.start_paypal()
        with mock.patch("apps.payouts.connect._http", side_effect=ConnectError("The provider refused the request. Please try again.")):
            r = self.callback(code="C", state=state)
        self.assertRedirects(r, self.url)
        self.assertFalse(PayoutMethod.objects.exists())

    def test_same_paypal_account_cannot_be_used_by_two_shops(self):
        other = make_seller("other@example.com")
        PayoutMethod.objects.create(shop=other.shop, kind="paypal", external_id="PAYER123", label="PayPal", status="connected", payouts_enabled=True)
        _r, state = self.start_paypal()
        with paypal_http():
            self.callback(code="C", state=state)
        self.assertFalse(PayoutMethod.objects.filter(shop=self.shop).exists())

    def test_reconnect_updates_instead_of_duplicating(self):
        for _ in range(2):
            _r, state = self.start_paypal()
            with paypal_http():
                self.callback(code="C", state=state)
        self.assertEqual(PayoutMethod.objects.filter(shop=self.shop, kind="paypal").count(), 1)

    def test_callback_requires_login(self):
        self.assertEqual(self.client_class().get(reverse("dashboard:seller_paypal_callback"), {"code": "x", "state": "y"}).status_code, 302)


@override_settings(STRIPE_SECRET_KEY="sk_test_123", SITE_URL="https://market.test")
class StripeConnectTests(Base):
    def setUp(self):
        super().setUp()
        self.patcher = mock.patch("apps.payouts.connect.stripe")
        self.stripe = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.stripe.Account.create.return_value = {"id": "acct_123"}
        self.stripe.AccountLink.create.return_value = {"url": "https://connect.stripe.test/setup/abc"}

    def account(self, **over):
        data = {"payouts_enabled": True, "details_submitted": True,
                "external_accounts": {"data": [{"object": "card", "brand": "Visa", "last4": "4242", "country": "US", "currency": "usd"}]}}
        data.update(over)
        return data

    def test_connect_creates_express_account_and_redirects_to_stripe(self):
        r = self.client.post(self.url, {"action": "connect_stripe"})
        self.assertEqual((r.status_code, r["Location"]), (302, "https://connect.stripe.test/setup/abc"))
        kw = self.stripe.Account.create.call_args.kwargs
        self.assertEqual((kw["type"], kw["email"]), ("express", "seller@example.com"))
        self.assertEqual(kw["capabilities"], {"transfers": {"requested": True}})
        link = self.stripe.AccountLink.create.call_args.kwargs
        self.assertEqual(link["account"], "acct_123")
        self.assertEqual(link["return_url"], "https://market.test/dashboard/seller/payout-methods/stripe/return/")
        self.assertEqual(link["refresh_url"], "https://market.test/dashboard/seller/payout-methods/stripe/refresh/")
        m = PayoutMethod.objects.get()
        self.assertEqual((m.kind, m.external_id, m.status, m.payouts_enabled), ("stripe", "acct_123", "pending", False))
        self.assertEqual(self.stripe.api_key, "sk_test_123")

    def test_second_connect_reuses_the_same_stripe_account(self):
        self.client.post(self.url, {"action": "connect_stripe"})
        self.client.post(self.url, {"action": "connect_stripe"})
        self.assertEqual(self.stripe.Account.create.call_count, 1)
        self.assertEqual(self.stripe.AccountLink.create.call_count, 2)

    def test_return_marks_connected_with_card_details(self):
        self.client.post(self.url, {"action": "connect_stripe"})
        self.stripe.Account.retrieve.return_value = self.account()
        r = self.client.get(reverse("dashboard:seller_stripe_return"))
        self.assertRedirects(r, self.url)
        m = PayoutMethod.objects.get()
        self.assertEqual((m.status, m.payouts_enabled, m.brand, m.last4, m.currency, m.is_default), ("connected", True, "Visa", "4242", "USD", True))
        self.assertEqual(m.label, "Visa •••• 4242")
        self.assertNotIn("4242424242424242", m.label)

    def test_return_with_incomplete_setup_stays_pending(self):
        self.client.post(self.url, {"action": "connect_stripe"})
        self.stripe.Account.retrieve.return_value = {"payouts_enabled": False, "details_submitted": False, "external_accounts": {"data": []}}
        self.client.get(reverse("dashboard:seller_stripe_return"))
        m = PayoutMethod.objects.get()
        self.assertEqual((m.status, m.is_usable), ("pending", False))

    def test_under_review_account_is_restricted(self):
        self.client.post(self.url, {"action": "connect_stripe"})
        self.stripe.Account.retrieve.return_value = self.account(payouts_enabled=False)
        self.client.get(reverse("dashboard:seller_stripe_return"))
        self.assertEqual(PayoutMethod.objects.get().status, "restricted")

    def test_bank_account_label(self):
        self.client.post(self.url, {"action": "connect_stripe"})
        self.stripe.Account.retrieve.return_value = self.account(external_accounts={"data": [{"object": "bank_account", "bank_name": "BNP Paribas", "last4": "6789", "country": "FR", "currency": "eur"}]})
        self.client.get(reverse("dashboard:seller_stripe_return"))
        self.assertEqual(PayoutMethod.objects.get().label, "BNP Paribas •••• 6789")

    def test_stripe_error_is_safe_and_does_not_leak(self):
        self.stripe.Account.create.side_effect = RuntimeError("sk_test_123 secret details")
        r = self.client.post(self.url, {"action": "connect_stripe"}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "sk_test_123")
        self.assertFalse(PayoutMethod.objects.exists())

    @override_settings(STRIPE_SECRET_KEY="")
    def test_not_configured(self):
        self.assertContains(self.client.get(self.url), "Not available yet")
        self.client.post(self.url, {"action": "connect_stripe"})
        self.stripe.Account.create.assert_not_called()

    def test_return_without_account_just_redirects(self):
        self.assertRedirects(self.client.get(reverse("dashboard:seller_stripe_return")), self.url)


class ManageMethodsTests(Base):
    def make(self, shop, kind="paypal", ext="E1", **kw):
        return PayoutMethod.objects.create(shop=shop, kind=kind, external_id=ext, label=kw.pop("label", "PayPal · x"), status="connected", payouts_enabled=True, **kw)

    def test_disconnect_and_promote_other_as_default(self):
        a = self.make(self.shop, "paypal", "P1", is_default=True)
        b = self.make(self.shop, "stripe", "acct_1", label="Visa •••• 1111")
        with mock.patch("apps.payouts.connect.stripe", None):
            self.client.post(self.url, {"action": "disconnect", "method_id": a.pk})
        self.assertFalse(PayoutMethod.objects.filter(pk=a.pk).exists())
        b.refresh_from_db()
        self.assertTrue(b.is_default)

    def test_make_default(self):
        a = self.make(self.shop, "paypal", "P1", is_default=True)
        b = self.make(self.shop, "stripe", "acct_1")
        self.client.post(self.url, {"action": "make_default", "method_id": b.pk})
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual((a.is_default, b.is_default), (False, True))

    def test_cannot_touch_another_shops_method(self):
        other = make_seller("other@example.com")
        m = self.make(other.shop, "paypal", "OTHER")
        self.assertEqual(self.client.post(self.url, {"action": "disconnect", "method_id": m.pk}).status_code, 404)
        self.assertTrue(PayoutMethod.objects.filter(pk=m.pk).exists())

    def test_one_account_per_kind_per_shop(self):
        from django.db import IntegrityError, transaction
        self.make(self.shop, "paypal", "P1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make(self.shop, "paypal", "P2")


class PayoutRequiresMethodTests(Base):
    def verify(self):
        self.shop.kyc_status = "verified"
        self.shop.save()

    def test_payout_needs_a_connected_method(self):
        self.verify()
        with mock.patch("apps.payouts.services.seller_available", return_value=Decimal("100")):
            with self.assertRaisesMessage(PayoutError, "Connect a payout method first"):
                request_payout(self.shop, "50")
            PayoutMethod.objects.create(shop=self.shop, kind="stripe", external_id="acct_1", label="Visa •••• 4242", status="pending", payouts_enabled=False)
            with self.assertRaises(PayoutError):                          # onboarding non terminé : inutilisable
                request_payout(self.shop, "50")

    def test_payout_snapshots_the_destination(self):
        self.verify()
        PayoutMethod.objects.create(shop=self.shop, kind="paypal", external_id="P1", label="PayPal · je•••@example.com", status="connected", payouts_enabled=True, is_default=True)
        with mock.patch("apps.payouts.services.seller_available", return_value=Decimal("100")):
            p = request_payout(self.shop, "50")
        self.assertEqual((p.method_kind, p.destination), ("paypal", "PayPal · je•••@example.com"))

    def test_kyc_is_still_required_first(self):
        PayoutMethod.objects.create(shop=self.shop, kind="paypal", external_id="P1", label="PayPal", status="connected", payouts_enabled=True)
        with self.assertRaisesMessage(PayoutError, "verified identity"):
            request_payout(self.shop, "50")

    def test_admin_sees_destination(self):
        Payout.objects.create(shop=self.shop, amount=Decimal("50"), method_kind="paypal", destination="PayPal · je•••@example.com")
        admin = make_user("admin@example.com", role="admin")
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse("dashboard:admin_payouts")), "PayPal · je•••@example.com")

    def test_seller_payouts_page_prompts_to_connect(self):
        self.assertContains(self.client.get(reverse("dashboard:seller_payouts")), reverse("dashboard:seller_payout_methods"))
