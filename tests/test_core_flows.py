import io
import zipfile
from decimal import Decimal

from django.core import mail, signing
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.tokens import make_verify_token
from apps.commissions.models import LedgerEntry
from apps.commissions.services import seller_balance
from apps.core.files import validate_product_file
from apps.licenses.models import License
from apps.moderation.services import ModerationError, decide
from apps.orders.models import Order
from apps.orders.services import create_order, mark_order_paid, refund_order
from apps.payouts.services import PayoutError, request_payout

from .conftest_helpers import make_product, make_seller, make_user, seed


class PublicPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_public_pages_render(self):
        for name in ["core:home", "products:explore", "sellers:pricing", "sellers:list", "core:about", "core:download", "core:contact",
                     "accounts:login", "accounts:register", "core:faq", "core:license_guide"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for slug in ["privacy", "terms", "seller-terms", "cookies", "refund", "ip", "report", "retention"]:
            self.assertEqual(self.client.get(reverse("core:legal", args=[slug])).status_code, 200, slug)

    def test_healthz_manifest_sw(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        self.assertEqual(self.client.get("/manifest.webmanifest").status_code, 200)
        self.assertEqual(self.client.get("/service-worker.js")["Service-Worker-Allowed"], "/")

    def test_pricing_from_database(self):
        r = self.client.get(reverse("sellers:pricing"))
        self.assertContains(r, "Starter")
        self.assertContains(r, "Pro")

    def test_light_background_token(self):
        css = open("static/css/tokens.css").read()
        self.assertIn("--color-bg: #F8F9FA", css)


class AuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_register_requires_email_confirmation(self):
        r = self.client.post(reverse("accounts:register"), {"display_name": "A", "email": "a@example.com", "password1": "Str0ng-pass-123!",
                                                           "password2": "Str0ng-pass-123!", "accept_terms": "on"})
        self.assertRedirects(r, reverse("accounts:verify_sent"))
        u = User.objects.get(email="a@example.com")
        self.assertFalse(u.email_verified)
        r = self.client.post(reverse("accounts:login"), {"username": "a@example.com", "password": "Str0ng-pass-123!"})
        self.assertEqual(r.status_code, 200)   # refusé tant que non confirmé
        self.client.get(reverse("accounts:verify", args=[make_verify_token(u)]))
        u.refresh_from_db()
        self.assertTrue(u.email_verified)
        r = self.client.post(reverse("accounts:login"), {"username": "a@example.com", "password": "Str0ng-pass-123!"})
        self.assertEqual(r.status_code, 302)

    def test_weak_password_rejected(self):
        r = self.client.post(reverse("accounts:register"), {"display_name": "A", "email": "b@example.com", "password1": "12345678",
                                                           "password2": "12345678", "accept_terms": "on"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(email="b@example.com").exists())

    def test_bad_token_rejected(self):
        self.assertEqual(self.client.get(reverse("accounts:verify", args=["garbage"])).status_code, 400)

    def test_lockout_after_failures(self):
        make_user("l@example.com")
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"username": "l@example.com", "password": "wrong"})
        r = self.client.post(reverse("accounts:login"), {"username": "l@example.com", "password": "Str0ng-pass-123!"})
        self.assertEqual(r.status_code, 200)

    def test_password_reset_sends_email(self):
        make_user("r@example.com")
        self.client.post(reverse("accounts:password_reset"), {"email": "r@example.com"})
        self.assertEqual(len(mail.outbox), 1)


class PermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_dashboard_requires_login(self):
        self.assertEqual(self.client.get(reverse("dashboard:buyer_home")).status_code, 302)

    def test_buyer_cannot_open_seller_or_admin(self):
        u = make_user("b@example.com")
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("dashboard:seller_home")).status_code, 302)   # -> become seller
        self.assertEqual(self.client.get(reverse("dashboard:admin_home")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:admin_users")).status_code, 403)

    def test_moderator_cannot_open_admin_only_pages(self):
        m = make_user("m@example.com", role="moderator")
        self.client.force_login(m)
        self.assertEqual(self.client.get(reverse("dashboard:admin_moderation")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:admin_users")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:admin_payouts")).status_code, 403)

    def test_seller_pages_render(self):
        s = make_seller()
        self.client.force_login(s)
        for n in ["seller_home", "seller_products", "seller_sales", "seller_revenue", "seller_payouts", "seller_reviews", "seller_shop", "seller_verification", "product_new"]:
            self.assertEqual(self.client.get(reverse(f"dashboard:{n}")).status_code, 200, n)

    def test_seller_cannot_edit_other_sellers_product(self):
        a, b = make_seller("a@example.com"), make_seller("b2@example.com")
        p = make_product(a, status="draft")
        self.client.force_login(b)
        self.assertEqual(self.client.get(reverse("dashboard:product_edit", args=[p.pk, "info"])).status_code, 404)


class ProductWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_pending_product_not_public_and_moderation(self):
        s = make_seller()
        p = make_product(s, status="pending")
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(reverse("products:explore")), p.title)
        m = make_user("mod@example.com", role="moderator")
        with self.assertRaises(ModerationError):
            decide(p, m, "rejected", "")   # raison obligatoire
        decide(p, m, "approved", "")
        p.refresh_from_db()
        self.assertEqual(p.status, "approved")
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 200)
        self.assertEqual(p.decisions.count(), 1)

    def test_filters_and_sorting(self):
        s = make_seller()
        make_product(s, "5.00", title="Cheap thing")
        make_product(s, "50.00", title="Pricey thing")
        r = self.client.get(reverse("products:explore"), {"min": "10"})
        self.assertContains(r, "Pricey thing")
        self.assertNotContains(r, "Cheap thing")
        self.assertEqual(self.client.get(reverse("products:explore"), {"sort": "price_asc", "q": "thing"}).status_code, 200)

    def test_zip_validation(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("ok.txt", "hi")
        validate_product_file(SimpleUploadedFile("ok.zip", buf.getvalue()))
        buf2 = io.BytesIO()
        with zipfile.ZipFile(buf2, "w") as z:
            z.writestr("../evil.txt", "x")
        with self.assertRaises(ValidationError):
            validate_product_file(SimpleUploadedFile("bad.zip", buf2.getvalue()))
        buf3 = io.BytesIO()
        with zipfile.ZipFile(buf3, "w") as z:
            z.writestr("setup.exe", "x")
        with self.assertRaises(ValidationError):
            validate_product_file(SimpleUploadedFile("exe.zip", buf3.getvalue()))
        with self.assertRaises(ValidationError):
            validate_product_file(SimpleUploadedFile("fake.zip", b"not a zip at all"))
        with self.assertRaises(ValidationError):
            validate_product_file(SimpleUploadedFile("a.exe", b"MZ"))


class OrderFinanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.seller = make_seller()
        self.buyer = make_user("buyer@example.com")
        self.product = make_product(self.seller, "100.00")

    def _paid_order(self):
        o = create_order(self.buyer, self.product, "personal")
        mark_order_paid(o.pk, "stripe", "cs_test_1")
        return o

    def test_commission_math_and_ledger(self):
        o = self._paid_order()
        item = o.items.get()
        self.assertEqual(item.commission_amount, Decimal("15.00"))   # Starter 15 %
        self.assertEqual(item.seller_amount, Decimal("85.00"))
        self.assertEqual(seller_balance(self.seller.shop), Decimal("85.00"))
        self.assertTrue(License.objects.filter(buyer=self.buyer, product=self.product).exists())
        self.assertTrue(hasattr(o, "invoice"))

    def test_mark_paid_is_idempotent(self):
        o = self._paid_order()
        _, changed = mark_order_paid(o.pk, "stripe", "cs_test_1")
        self.assertFalse(changed)
        self.assertEqual(LedgerEntry.objects.filter(shop=self.seller.shop).count(), 1)
        self.assertEqual(License.objects.count(), 1)

    def test_ledger_is_immutable(self):
        self._paid_order()
        e = LedgerEntry.objects.first()
        e.amount = Decimal("1.00")
        with self.assertRaises(RuntimeError):
            e.save()
        with self.assertRaises(RuntimeError):
            e.delete()
        with self.assertRaises(RuntimeError):
            LedgerEntry.objects.all().update(amount=0)

    def test_refund_reverses_ledger_and_revokes_license(self):
        o = self._paid_order()
        from apps.orders import services
        o.provider = "manual"
        o.save()
        refund_order(o.pk, make_user("adm@example.com", role="admin"))
        self.assertEqual(seller_balance(self.seller.shop), Decimal("0.00"))
        self.assertIsNotNone(License.objects.get().revoked_at)

    def test_cannot_buy_own_or_twice(self):
        from apps.orders.services import OrderError
        with self.assertRaises(OrderError):
            create_order(self.seller, self.product, "personal")
        self._paid_order()
        with self.assertRaises(OrderError):
            create_order(self.buyer, self.product, "personal")

    def test_checkout_in_catalog_mode_never_simulates_payment(self):
        self.client.force_login(self.buyer)
        r = self.client.post(reverse("orders:checkout", args=[self.product.slug]), {"license": "personal"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Order.objects.filter(status="paid").exists())
        self.assertFalse(License.objects.exists())

    def test_free_product_goes_to_library(self):
        free = make_product(self.seller, "0.00", title="Free thing")
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:checkout", args=[free.slug]), {"license": "personal"})
        self.assertTrue(License.objects.filter(buyer=self.buyer, product=free).exists())

    def test_payout_requires_kyc(self):
        self._paid_order()
        with self.assertRaises(PayoutError):
            request_payout(self.seller.shop, "20")


class DownloadSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.seller = make_seller()
        self.buyer = make_user("buyer@example.com")
        self.other = make_user("other@example.com")
        self.product = make_product(self.seller, "0.00")
        o = create_order(self.buyer, self.product, "personal")
        mark_order_paid(o.pk, "free", "free-x")
        self.lic = License.objects.get()
        self.ver = self.product.versions.first()

    def test_owner_can_download(self):
        self.client.force_login(self.buyer)
        r = self.client.post(reverse("downloads:request", args=[self.lic.pk, self.ver.pk]))
        self.assertEqual(r.status_code, 302)
        r2 = self.client.get(r["Location"])
        self.assertEqual(r2.status_code, 200)
        self.assertIn("attachment", r2["Content-Disposition"])

    def test_other_user_forbidden(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("downloads:request", args=[self.lic.pk, self.ver.pk])).status_code, 404)

    def test_token_tied_to_user(self):
        from apps.orders.downloads import make_token
        token = make_token(self.buyer, self.lic, self.ver)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("downloads:serve", args=[token])).status_code, 403)

    def test_tampered_token_rejected(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse("downloads:serve", args=["bad.token.value"])).status_code, 403)

    def test_revoked_license_blocked(self):
        from apps.orders.downloads import make_token
        from django.utils import timezone
        self.lic.revoked_at = timezone.now()
        self.lic.save()
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse("downloads:serve", args=[make_token(self.buyer, self.lic, self.ver)])).status_code, 404)

    def test_unsafe_version_blocked(self):
        self.ver.scan_status = "infected"
        self.ver.save()
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post(reverse("downloads:request", args=[self.lic.pk, self.ver.pk])).status_code, 404)

    def test_files_not_under_public_media(self):
        from django.conf import settings
        self.assertNotIn(str(settings.MEDIA_ROOT), str(settings.PRIVATE_FILES_ROOT))


@override_settings(PAYMENT_PROVIDER="stripe", STRIPE_SECRET_KEY="sk_test_x", STRIPE_WEBHOOK_SECRET="whsec_x")
class WebhookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_unsigned_webhook_rejected(self):
        r = self.client.post("/payments/webhook/stripe/", data="{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="bad")
        self.assertEqual(r.status_code, 400)

    def test_webhook_for_unconfigured_provider_404(self):
        with self.settings(PAYMENT_PROVIDER=""):
            self.assertEqual(self.client.post("/payments/webhook/stripe/", data="{}", content_type="application/json").status_code, 404)

    def test_process_webhook_idempotent_and_amount_checked(self):
        from apps.payments.providers.base import PaymentError, WebhookResult
        from apps.payments.services import process_webhook
        seller, buyer = make_seller(), make_user("wb@example.com")
        o = create_order(buyer, make_product(seller, "20.00"), "personal")
        with self.assertRaises(PaymentError):
            process_webhook(WebhookResult(event_id="e0", event_type="x", order_number=o.number, paid=True, amount_cents=1))
        res = WebhookResult(event_id="e1", event_type="x", order_number=o.number, paid=True, amount_cents=2000, provider_ref="cs_1", payment_ref="pi_1")
        process_webhook(res)
        process_webhook(res)
        o.refresh_from_db()
        self.assertEqual(o.status, "paid")
        self.assertEqual(License.objects.count(), 1)
        self.assertEqual(LedgerEntry.objects.filter(entry_type="sale_earning").count(), 1)


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_api_lists_only_approved(self):
        s = make_seller()
        make_product(s, title="Visible one")
        make_product(s, status="draft", title="Hidden draft")
        r = self.client.get("/api/v1/products/")
        self.assertEqual(r.status_code, 200)
        titles = [x["title"] for x in r.json()["results"]]
        self.assertIn("Visible one", titles)
        self.assertNotIn("Hidden draft", titles)

    def test_api_is_read_only(self):
        self.assertEqual(self.client.post("/api/v1/products/", {}).status_code in (403, 405), True)
