"""Profil avancé : identifiant public, avatar/couverture, liens, visibilité et page partageable /u/<username>/."""
import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.forms import ProfileForm
from apps.accounts.models import User

from .conftest_helpers import make_product, make_seller, make_user, seed

TMP_MEDIA = tempfile.mkdtemp(prefix="indpns-test-media-")


def read_field(fieldfile):
    """Contenu binaire d'un champ image, quel que soit le stockage (disque ou base de données)."""
    fieldfile.open("rb")
    try:
        return fieldfile.read()
    finally:
        fieldfile.close()


def png(size=(800, 600), fmt="PNG", name="photo.png", color=(30, 90, 200)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def base_data(**over):
    data = {"display_name": "Jean Dupont", "username": "", "headline": "", "bio": "", "location": "", "website": "",
            "github": "", "twitter": "", "linkedin": "", "preferred_language": "en"}
    data.update(over)
    return data


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ProfileFormTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = make_user("jean@example.com", display_name="Jean")

    def form(self, data=None, files=None, user=None):
        return ProfileForm(data or base_data(), files, instance=user or self.user)

    def test_username_rules(self):
        for bad in ["ab", "-abc", "abc-", "a b", "x" * 31, "admin", "indpns", "support"]:
            f = self.form(base_data(username=bad))
            self.assertFalse(f.is_valid(), bad)
            self.assertIn("username", f.errors, bad)

    def test_username_is_normalized_to_lowercase(self):
        f = self.form(base_data(username="  @Jean-Dupont "))
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.save().username, "jean-dupont")

    def test_username_unique_case_insensitive(self):
        other = make_user("other@example.com")
        other.username = "taken"
        other.save()
        f = self.form(base_data(username="TAKEN"))
        self.assertFalse(f.is_valid())
        self.assertIn("username", f.errors)

    def test_public_profile_requires_username(self):
        f = self.form(base_data(profile_public="on"))
        self.assertFalse(f.is_valid())
        self.assertIn("username", f.errors)
        f = self.form(base_data(profile_public="on", username="jean"))
        self.assertTrue(f.is_valid(), f.errors)

    def test_social_handles_accept_urls(self):
        f = self.form(base_data(github="https://github.com/octocat", twitter="@jdupont",
                                linkedin="https://www.linkedin.com/in/jean-dupont-123/"))
        self.assertTrue(f.is_valid(), f.errors)
        u = f.save()
        self.assertEqual((u.github, u.twitter, u.linkedin), ("octocat", "jdupont", "jean-dupont-123"))

    def test_social_handle_wrong_host_rejected(self):
        f = self.form(base_data(github="https://evil.example/octocat"))
        self.assertFalse(f.is_valid())
        self.assertIn("github", f.errors)

    def test_website_must_be_http(self):
        self.assertFalse(self.form(base_data(website="javascript:alert(1)")).is_valid())
        f = self.form(base_data(website="example.com"))
        self.assertTrue(f.is_valid(), f.errors)
        self.assertTrue(f.save().website.startswith("https://"))

    def test_avatar_is_validated_resized_and_converted(self):
        f = self.form(files={"avatar": png((1200, 800))})
        self.assertTrue(f.is_valid(), f.errors)
        u = f.save()
        self.assertTrue(u.avatar.name.startswith("profiles/avatars/") and u.avatar.name.endswith(".webp"))
        self.assertNotIn("photo", u.avatar.name)                      # le nom d'origine n'est jamais conservé
        with Image.open(io.BytesIO(read_field(u.avatar))) as img:
            self.assertEqual((img.size, img.format), ((512, 512), "WEBP"))

    def test_cover_is_cropped_to_banner_ratio(self):
        u = self.form(files={"cover": png((2400, 1500))}).save()
        with Image.open(io.BytesIO(read_field(u.cover))) as img:
            self.assertEqual(img.size, (1500, 500))

    def test_exif_metadata_is_stripped(self):
        buf = io.BytesIO()
        exif = Image.Exif()
        exif[0x010F] = "SecretCamera"
        Image.new("RGB", (800, 800), (10, 10, 10)).save(buf, "JPEG", exif=exif)
        f = self.form(files={"avatar": SimpleUploadedFile("a.jpg", buf.getvalue(), content_type="image/jpeg")})
        self.assertTrue(f.is_valid(), f.errors)
        u = f.save()
        self.assertNotIn(b"SecretCamera", read_field(u.avatar))

    def test_fake_image_rejected(self):
        fake = SimpleUploadedFile("evil.png", b"<?php system($_GET['c']); ?>", content_type="image/png")
        f = self.form(files={"avatar": fake})
        self.assertFalse(f.is_valid())
        self.assertIn("avatar", f.errors)

    def test_svg_and_gif_rejected(self):
        svg = SimpleUploadedFile("a.svg", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", content_type="image/svg+xml")
        self.assertFalse(self.form(files={"avatar": svg}).is_valid())
        self.assertFalse(self.form(files={"avatar": png(fmt="GIF", name="a.gif")}).is_valid())

    def test_tiny_image_rejected(self):
        f = self.form(files={"avatar": png((50, 50))})
        self.assertFalse(f.is_valid())
        self.assertIn("avatar", f.errors)

    def test_replacing_and_removing_images_deletes_old_files(self):
        u = self.form(files={"avatar": png()}).save()
        old, storage = u.avatar.name, u.avatar.storage
        self.assertTrue(storage.exists(old))
        u = self.form(files={"avatar": png(color=(200, 50, 50))}, user=User.objects.get(pk=u.pk)).save()
        self.assertNotEqual(old, u.avatar.name)
        self.assertFalse(storage.exists(old))
        newest = u.avatar.name
        f = self.form(base_data(remove_avatar="on"), user=User.objects.get(pk=u.pk))
        self.assertTrue(f.is_valid(), f.errors)
        u = f.save()
        self.assertFalse(u.avatar)
        self.assertFalse(storage.exists(newest))

    def test_keeping_form_untouched_keeps_images(self):
        u = self.form(files={"avatar": png()}).save()
        name = u.avatar.name
        u = self.form(base_data(display_name="Jean D."), user=User.objects.get(pk=u.pk)).save()
        self.assertEqual(u.avatar.name, name)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class PublicProfilePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.user = make_user("pub@example.com", display_name="Marie Curie")
        self.user.username = "marie"
        self.user.headline = "Physicist"
        self.user.bio = "Hello <script>alert(1)</script> world"
        self.user.save()
        self.url = reverse("profiles:detail", args=["marie"])

    def test_private_by_default_is_404_for_visitors(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_owner_sees_private_preview_noindex(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "noindex")
        self.assertContains(r, "Private preview")

    def test_other_users_cannot_see_private_profile(self):
        self.client.force_login(make_user("other@example.com"))
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_public_profile_is_visible_without_login(self):
        self.user.profile_public = True
        self.user.save()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Marie Curie")
        self.assertContains(r, "Physicist")
        self.assertNotContains(r, "noindex")
        self.assertNotContains(r, "pub@example.com")                  # l'e-mail n'est jamais affiché
        self.assertContains(r, 'rel="canonical"')

    def test_bio_is_escaped_no_xss(self):
        self.user.profile_public = True
        self.user.save()
        r = self.client.get(self.url)
        self.assertNotContains(r, "<script>alert(1)</script>")
        self.assertContains(r, "&lt;script&gt;")

    def test_uppercase_url_redirects_to_canonical(self):
        self.user.profile_public = True
        self.user.save()
        r = self.client.get(reverse("profiles:detail", args=["MARIE"]))
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r["Location"], self.url)

    def test_unknown_and_inactive_users_are_404(self):
        self.assertEqual(self.client.get(reverse("profiles:detail", args=["nobody"])).status_code, 404)
        self.user.profile_public = True
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_external_links_are_safe(self):
        self.user.profile_public = True
        self.user.website = "https://example.com"
        self.user.github = "octocat"
        self.user.save()
        r = self.client.get(self.url)
        self.assertContains(r, "https://github.com/octocat")
        self.assertContains(r, "nofollow noopener noreferrer ugc")

    def test_seller_profile_lists_products(self):
        seller = make_seller("vendor@example.com")
        seller.username, seller.profile_public = "vendor", True
        seller.save()
        make_product(seller, title="Super kit")
        r = self.client.get(reverse("profiles:detail", args=["vendor"]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Super kit")
        self.assertContains(r, "Visit shop")


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ProfileSettingsViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.user = make_user("edit@example.com", display_name="Edit Me")
        self.url = reverse("dashboard:buyer_profile")

    def test_requires_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_page_renders_with_upload_form(self):
        self.client.force_login(self.user)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'enctype="multipart/form-data"')
        self.assertContains(r, 'name="avatar"')
        self.assertContains(r, 'name="cover"')

    def test_post_saves_profile_and_exposes_share_link(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url, {**base_data(display_name="Edit Me", username="edit-me", headline="Dev",
                                                    bio="Line 1\nLine 2", profile_public="on"), "avatar": png(), "cover": png((1600, 700))})
        self.assertRedirects(r, self.url)
        u = User.objects.get(pk=self.user.pk)
        self.assertEqual((u.username, u.headline, u.profile_public), ("edit-me", "Dev", True))
        self.assertTrue(u.avatar and u.cover)
        page = self.client.get(self.url)
        self.assertContains(page, "/u/edit-me/")
        self.assertEqual(self.client.logout() or self.client.get(reverse("profiles:detail", args=["edit-me"])).status_code, 200)

    def test_invalid_image_shows_error_and_changes_nothing(self):
        self.client.force_login(self.user)
        bad = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
        r = self.client.post(self.url, {**base_data(display_name="Changed"), "avatar": bad})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.get(pk=self.user.pk).display_name, "Edit Me")
