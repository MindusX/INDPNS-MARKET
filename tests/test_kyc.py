"""Vérification d'identité (KYC) : soumission, chiffrement des documents, revue par l'équipe, accès sécurisé."""
import io
from datetime import date, timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.core import crypto
from apps.core.models import AuditLog
from apps.notifications.models import Notification
from apps.sellers import kyc
from apps.sellers.models import IdentityVerification, KycDocument

from .conftest_helpers import make_seller, make_user, seed


def photo(size=(900, 600), color=(40, 90, 160), fmt="PNG", name="doc.png"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def form_data(**over):
    born = date.today().replace(year=date.today().year - 30)
    data = {"action": "identity", "first_name": "Jean", "last_name": "Dupont", "date_of_birth": born.isoformat(), "nationality": "FR",
            "address_line1": "12 rue de la Paix", "city": "Paris", "postal_code": "75002", "country": "FR", "phone": "+33 6 12 34 56 78",
            "doc_type": "national_id", "doc_country": "FR", "consent": "on"}
    data.update(over)
    return data


def files(**over):
    f = {"front": photo(), "back": photo(color=(10, 10, 10)), "selfie": photo(color=(200, 150, 120))}
    f.update(over)
    return {k: v for k, v in f.items() if v is not None}


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.user = make_seller("seller@example.com")
        self.shop = self.user.shop
        self.client.force_login(self.user)
        self.url = reverse("dashboard:seller_verification")

    def submit(self, data=None, fl=None):
        return self.client.post(self.url, {**(data or form_data()), **(fl if fl is not None else files())})

    def pending(self):
        self.submit()
        return IdentityVerification.objects.get()


class SubmissionTests(Base):
    def test_page_renders_form_for_new_seller(self):
        r = self.client.get(self.url)
        self.assertContains(r, 'enctype="multipart/form-data"')
        self.assertContains(r, 'name="front"')
        self.assertContains(r, "Submit for verification")

    def test_successful_submission(self):
        r = self.submit()
        self.assertRedirects(r, self.url)
        v = IdentityVerification.objects.get()
        self.assertEqual((v.shop, v.status, v.full_name, v.doc_type), (self.shop, "pending", "Jean Dupont", "national_id"))
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.kyc_status, "pending")
        self.assertEqual(set(v.documents.values_list("kind", flat=True)), {"front", "back", "selfie"})
        self.assertTrue(AuditLog.objects.filter(action="kyc.submitted", actor=self.user).exists())

    def test_documents_are_encrypted_at_rest_and_roundtrip(self):
        self.submit()
        doc = KycDocument.objects.get(kind="front")
        raw = bytes(doc.data)
        self.assertFalse(raw.startswith(b"\xff\xd8"))                    # pas un JPEG en clair
        self.assertNotIn(b"JFIF", raw[:64])
        plain = kyc.document_bytes(doc)
        self.assertTrue(plain.startswith(b"\xff\xd8"))                   # JPEG une fois déchiffré
        Image.open(io.BytesIO(plain)).verify()

    def test_passport_does_not_need_a_back_side(self):
        r = self.submit(form_data(doc_type="passport"), files(back=None))
        self.assertRedirects(r, self.url)
        self.assertEqual(KycDocument.objects.count(), 2)

    def test_id_card_requires_back_side(self):
        r = self.submit(form_data(doc_type="national_id"), files(back=None))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(IdentityVerification.objects.exists())
        self.assertContains(r, "This file is required.")

    def test_selfie_and_front_are_required(self):
        for missing in ("selfie", "front"):
            r = self.submit(fl=files(**{missing: None}))
            self.assertEqual(r.status_code, 200, missing)
        self.assertFalse(IdentityVerification.objects.exists())

    def test_must_be_18_or_older(self):
        young = (date.today() - timedelta(days=365 * 17)).isoformat()
        r = self.submit(form_data(date_of_birth=young))
        self.assertContains(r, "at least 18")
        self.assertFalse(IdentityVerification.objects.exists())

    def test_consent_required(self):
        data = form_data()
        data.pop("consent")
        self.assertEqual(self.submit(data).status_code, 200)
        self.assertFalse(IdentityVerification.objects.exists())

    def test_rejects_non_images_pdf_and_tiny_files(self):
        bad = [SimpleUploadedFile("x.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
               SimpleUploadedFile("x.png", b"<?php system($_GET[1]); ?>", content_type="image/png"),
               photo((200, 150))]
        for b in bad:
            r = self.submit(fl=files(front=b))
            self.assertEqual(r.status_code, 200)
            self.assertFalse(IdentityVerification.objects.exists())

    def test_invalid_names_and_phone(self):
        self.assertEqual(self.submit(form_data(first_name="J3an<script>")).status_code, 200)
        self.assertEqual(self.submit(form_data(phone="abc")).status_code, 200)
        self.assertFalse(IdentityVerification.objects.exists())

    def test_cannot_submit_twice_while_pending(self):
        self.pending()
        self.submit()
        self.assertEqual(IdentityVerification.objects.count(), 1)
        self.assertEqual(KycDocument.objects.count(), 3)

    def test_requires_seller_login(self):
        self.assertEqual(self.client_class().get(self.url).status_code, 302)

    @override_settings(KYC_KEY_CONFIGURED=False, KYC_ENCRYPTION_KEY="")
    def test_blocked_when_no_stable_encryption_key(self):
        self.assertContains(self.client.get(self.url), "temporarily unavailable")
        self.submit()
        self.assertFalse(IdentityVerification.objects.exists())


class ReviewTests(Base):
    def setUp(self):
        super().setUp()
        self.v = self.pending()
        self.admin = make_user("admin@example.com", role="admin")

    def as_admin(self):
        c = self.client_class()
        c.force_login(self.admin)
        return c

    def test_only_admins_can_access_the_queue(self):
        self.assertEqual(self.client.get(reverse("dashboard:admin_kyc")).status_code, 403)          # vendeur
        mod = self.client_class()
        mod.force_login(make_user("mod@example.com", role="moderator"))
        self.assertEqual(mod.get(reverse("dashboard:admin_kyc")).status_code, 403)                   # modérateur : pas assez
        self.assertEqual(self.client_class().get(reverse("dashboard:admin_kyc")).status_code, 302)
        r = self.as_admin().get(reverse("dashboard:admin_kyc"))
        self.assertContains(r, "Jean Dupont")

    def test_detail_shows_data_and_logs_access(self):
        r = self.as_admin().get(reverse("dashboard:admin_kyc_detail", args=[self.v.pk]))
        self.assertContains(r, "12 rue de la Paix")
        self.assertTrue(AuditLog.objects.filter(action="kyc.viewed", actor=self.admin).exists())

    def test_approve_unlocks_payout_eligibility(self):
        r = self.as_admin().post(reverse("dashboard:admin_kyc_detail", args=[self.v.pk]), {"action": "approve"})
        self.assertRedirects(r, reverse("dashboard:admin_kyc"))
        self.v.refresh_from_db(); self.shop.refresh_from_db()
        self.assertEqual((self.v.status, self.v.reviewed_by, self.shop.kyc_status), ("approved", self.admin, "verified"))
        self.assertTrue(self.shop.is_payout_eligible)
        self.assertTrue(Notification.objects.filter(user=self.user, kind="kyc", title="Identity verified").exists())
        self.assertTrue(AuditLog.objects.filter(action="kyc.approved").exists())

    def test_reject_requires_reason_then_allows_resubmission(self):
        url = reverse("dashboard:admin_kyc_detail", args=[self.v.pk])
        self.as_admin().post(url, {"action": "reject", "reason": "  "})
        self.v.refresh_from_db()
        self.assertEqual(self.v.status, "pending")                                                   # refus sans motif impossible
        self.as_admin().post(url, {"action": "reject", "reason": "The photo is blurry."})
        self.v.refresh_from_db(); self.shop.refresh_from_db()
        self.assertEqual((self.v.status, self.shop.kyc_status), ("rejected", "rejected"))
        page = self.client.get(self.url)
        self.assertContains(page, "The photo is blurry.")                                           # le vendeur voit le motif
        self.assertContains(page, 'name="front"')                                                   # et peut renvoyer son dossier
        self.assertRedirects(self.submit(), self.url)
        self.assertEqual(IdentityVerification.objects.count(), 2)

    def test_cannot_process_twice(self):
        kyc.approve(self.v.pk, self.admin)
        with self.assertRaises(kyc.KycError):
            kyc.reject(self.v.pk, self.admin, "late")
        with self.assertRaises(kyc.KycError):
            kyc.approve(self.v.pk, self.admin)

    def test_admin_cannot_review_their_own_shop(self):
        self.user.role = "admin"
        self.user.save()
        self.assertEqual(self.client.get(reverse("dashboard:admin_kyc_detail", args=[self.v.pk])).status_code, 403)

    @override_settings(KYC_PURGE_DOCS_ON_APPROVAL=True)
    def test_documents_can_be_purged_on_approval(self):
        kyc.approve(self.v.pk, self.admin)
        self.assertFalse(KycDocument.objects.exclude(data=None).exists())


class DocumentAccessTests(Base):
    def setUp(self):
        super().setUp()
        self.v = self.pending()
        self.doc = self.v.documents.get(kind="front")
        self.url_doc = reverse("dashboard:admin_kyc_document", args=[self.v.pk, self.doc.pk])
        self.admin = make_user("admin@example.com", role="admin")

    def test_admin_gets_decrypted_image_with_no_cache_and_audit(self):
        c = self.client_class()
        c.force_login(self.admin)
        r = c.get(self.url_doc)
        self.assertEqual((r.status_code, r["Content-Type"]), (200, "image/jpeg"))
        self.assertIn("no-store", r["Cache-Control"])
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        Image.open(io.BytesIO(r.content)).verify()
        self.assertTrue(AuditLog.objects.filter(action="kyc.document_viewed", actor=self.admin).exists())

    def test_seller_anonymous_and_moderator_cannot_view(self):
        self.assertEqual(self.client.get(self.url_doc).status_code, 403)                            # même le propriétaire du dossier
        self.assertEqual(self.client_class().get(self.url_doc).status_code, 302)
        mod = self.client_class()
        mod.force_login(make_user("mod@example.com", role="moderator"))
        self.assertEqual(mod.get(self.url_doc).status_code, 403)

    def test_document_must_belong_to_the_verification(self):
        c = self.client_class()
        c.force_login(self.admin)
        self.assertEqual(c.get(reverse("dashboard:admin_kyc_document", args=[self.v.pk + 99, self.doc.pk])).status_code, 404)

    def test_purged_document_is_gone(self):
        KycDocument.objects.filter(pk=self.doc.pk).update(data=None)
        c = self.client_class()
        c.force_login(self.admin)
        self.assertEqual(c.get(self.url_doc).status_code, 410)

    def test_images_are_never_in_a_public_url(self):
        self.assertEqual(self.client_class().get("/media/kyc/anything.jpg").status_code, 404)


class CryptoTests(TestCase):
    @override_settings(KYC_ENCRYPTION_KEY="", KYC_KEY_CONFIGURED=True, SECRET_KEY="a-stable-secret")
    def test_derived_key_roundtrip(self):
        self.assertEqual(crypto.decrypt_bytes(crypto.encrypt_bytes(b"secret")), b"secret")

    def test_explicit_key_roundtrip_and_wrong_key_fails(self):
        k1, k2 = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        with override_settings(KYC_ENCRYPTION_KEY=k1, KYC_KEY_CONFIGURED=True):
            token = crypto.encrypt_bytes(b"data")
        with override_settings(KYC_ENCRYPTION_KEY=k2, KYC_KEY_CONFIGURED=True):
            with self.assertRaises(InvalidToken):
                crypto.decrypt_bytes(token)

    def test_key_rotation(self):
        old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        with override_settings(KYC_ENCRYPTION_KEY=old, KYC_KEY_CONFIGURED=True):
            token = crypto.encrypt_bytes(b"data")
        with override_settings(KYC_ENCRYPTION_KEY=f"{new},{old}", KYC_KEY_CONFIGURED=True):      # la nouvelle chiffre, les deux déchiffrent
            self.assertEqual(crypto.decrypt_bytes(token), b"data")
            self.assertNotEqual(crypto.encrypt_bytes(b"data")[:20], token[:20])

    @override_settings(KYC_ENCRYPTION_KEY="", KYC_KEY_CONFIGURED=False)
    def test_refuses_without_any_stable_key(self):
        from django.core.exceptions import ImproperlyConfigured
        with self.assertRaises(ImproperlyConfigured):
            crypto.encrypt_bytes(b"x")

    @override_settings(KYC_ENCRYPTION_KEY="not-a-valid-key", KYC_KEY_CONFIGURED=True)
    def test_invalid_key_is_reported(self):
        from django.core.exceptions import ImproperlyConfigured
        with self.assertRaises(ImproperlyConfigured):
            crypto.encrypt_bytes(b"x")
