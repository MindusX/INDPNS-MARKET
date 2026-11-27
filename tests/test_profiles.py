"""Profil avancé : identifiant public, avatar/couverture, liens, visibilité et page partageable /u/<username>/."""
import io
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from apps.accounts.forms import ProfileForm
from apps.accounts.models import User

from .conftest_helpers import make_product, make_seller, make_user, seed

def png(size=(800, 600), fmt="PNG", name="photo.png", color=(30, 90, 200)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def base_data(**over):
    data = {"display_name": "Jean Dupont", "username": "", "headline": "", "bio": "", "location": "", "website": "",
            "github": "", "twitter": "", "linkedin": "", "preferred_language": "en"}
    data.update(over)
    return data


class ProfileFormTests(TestCase):
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
        self.assertContains(r, 'id="pf-file-avatar"')
        self.assertContains(r, 'id="pf-file-cover"')
        self.assertContains(r, "/api/profile/upload-avatar")
        self.assertContains(r, 'id="pf-i18n"')

    def test_post_saves_profile_and_exposes_share_link(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url, {**base_data(display_name="Edit Me", username="edit-me", headline="Dev",
                                                    bio="Line 1\nLine 2", profile_public="on")})
        self.assertRedirects(r, self.url)
        u = User.objects.get(pk=self.user.pk)
        self.assertEqual((u.username, u.headline, u.profile_public), ("edit-me", "Dev", True))
        page = self.client.get(self.url)
        self.assertContains(page, "/u/edit-me/")
        self.assertEqual(self.client.logout() or self.client.get(reverse("profiles:detail", args=["edit-me"])).status_code, 200)


class ProfileImageApiTests(TestCase):
    """Images de profil stockées EN BASE et servies par /api/profile/avatar|cover/<id> — comme Mindus Forge."""

    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.user = make_user("img@example.com", display_name="Img User")
        self.client.force_login(self.user)

    def upload(self, kind="avatar", file=None, client=None):
        return (client or self.client).post(reverse(f"profiles:upload_{kind}"), {"file": file or png()})

    def fetch(self, url, client=None, **extra):
        return (client or self.client).get(url, **extra)

    def decode(self, response):
        return Image.open(io.BytesIO(response.content))

    def test_upload_avatar_is_square_jpeg_and_served(self):
        r = self.upload("avatar", png((1200, 800)))
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["success"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_avatar)
        self.assertIn(f"?v={self.user.avatar_version}", data["url"])
        img = self.fetch(data["url"])
        self.assertEqual(img.status_code, 200)
        self.assertEqual(img["Content-Type"], "image/jpeg")
        self.assertEqual(self.decode(img).size, (800, 800))

    def test_small_avatar_is_cropped_not_upscaled(self):
        self.upload("avatar", png((300, 200)))
        self.user.refresh_from_db()
        self.assertEqual(self.decode(self.fetch(self.user.avatar_url)).size, (200, 200))

    def test_cover_keeps_ratio_and_caps_width(self):
        self.assertTrue(self.upload("cover", png((3000, 1000))).json()["success"])
        self.user.refresh_from_db()
        self.assertEqual(self.decode(self.fetch(self.user.cover_url)).size, (2400, 800))
        self.assertEqual(self.user.cover_position_y, 50)

    def test_exif_metadata_is_stripped(self):
        buf = io.BytesIO()
        exif = Image.Exif()
        exif[0x010F] = "SecretCamera"
        Image.new("RGB", (900, 900), (10, 10, 10)).save(buf, "JPEG", exif=exif)
        self.upload("avatar", SimpleUploadedFile("a.jpg", buf.getvalue(), content_type="image/jpeg"))
        self.user.refresh_from_db()
        self.assertNotIn(b"SecretCamera", self.fetch(self.user.avatar_url).content)

    def test_transparent_png_is_flattened_on_white(self):
        buf = io.BytesIO()
        Image.new("RGBA", (400, 400), (0, 0, 0, 0)).save(buf, "PNG")
        self.upload("avatar", SimpleUploadedFile("t.png", buf.getvalue(), content_type="image/png"))
        self.user.refresh_from_db()
        px = self.decode(self.fetch(self.user.avatar_url)).convert("RGB").getpixel((10, 10))
        self.assertTrue(all(c >= 250 for c in px), px)

    def test_rejects_fake_and_dangerous_files(self):
        for name, payload in [("evil.png", b"<?php system($_GET['c']); ?>"),
                              ("x.svg", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"),
                              ("empty.png", b"")]:
            r = self.upload("avatar", SimpleUploadedFile(name, payload, content_type="image/png"))
            self.assertEqual(r.status_code, 400, name)
            self.assertFalse(r.json()["success"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_avatar)

    def test_missing_file_is_400(self):
        self.assertEqual(self.client.post(reverse("profiles:upload_avatar"), {}).status_code, 400)

    def test_upload_requires_login(self):
        r = self.client_class().post(reverse("profiles:upload_avatar"), {"file": png()})
        self.assertEqual(r.status_code, 401)
        self.assertFalse(r.json()["success"])

    def test_each_upload_changes_the_versioned_url(self):
        self.upload("avatar")
        self.user.refresh_from_db()
        first = self.user.avatar_url
        self.upload("avatar", png(color=(200, 50, 50)))
        self.user.refresh_from_db()
        self.assertNotEqual(first, self.user.avatar_url)

    def test_private_profile_images_are_hidden_from_others(self):
        self.upload("avatar")
        self.user.refresh_from_db()
        url = self.user.avatar_url
        self.assertEqual(self.fetch(url).status_code, 200)                              # le propriétaire
        self.assertEqual(self.fetch(url, client=self.client_class()).status_code, 404)  # visiteur : profil privé
        other = self.client_class()
        other.force_login(make_user("other@example.com"))
        self.assertEqual(self.fetch(url, client=other).status_code, 404)
        staff = self.client_class()
        staff.force_login(make_user("staff@example.com", is_staff=True))
        self.assertEqual(self.fetch(url, client=staff).status_code, 200)                # l'équipe peut modérer

    def test_public_profile_images_are_visible_to_everyone(self):
        self.upload("avatar")
        self.user.username, self.user.profile_public = "imguser", True
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.fetch(self.user.avatar_url, client=self.client_class()).status_code, 200)

    def test_etag_returns_304_and_cache_is_immutable(self):
        self.upload("avatar")
        self.user.refresh_from_db()
        r = self.fetch(self.user.avatar_url)
        self.assertIn("immutable", r["Cache-Control"])
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.fetch(self.user.avatar_url, HTTP_IF_NONE_MATCH=r["ETag"]).status_code, 304)

    def test_delete_avatar_and_cover(self):
        self.upload("avatar")
        self.upload("cover")
        self.assertTrue(self.client.delete(reverse("profiles:delete_avatar")).json()["success"])
        self.assertTrue(self.client.delete(reverse("profiles:delete_cover")).json()["success"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_avatar or self.user.has_cover)
        self.assertEqual(self.fetch(reverse("profiles:avatar", args=[self.user.pk])).status_code, 404)

    def test_cover_position(self):
        url = reverse("profiles:cover_position")
        put = lambda body: self.client.put(url, data=json.dumps(body), content_type="application/json")
        self.assertEqual(put({"position_y": 30}).status_code, 400)                      # pas encore de couverture
        self.upload("cover")
        self.assertEqual(put({"position_y": 30}).json()["position_y"], 30)
        self.user.refresh_from_db()
        self.assertEqual(self.user.cover_position_y, 30)
        for bad in (150, -1, "abc", None):
            self.assertEqual(put({"position_y": bad}).status_code, 400, bad)

    def test_wrong_methods_are_rejected(self):
        self.assertEqual(self.client.get(reverse("profiles:upload_avatar")).status_code, 405)
        self.assertEqual(self.client.post(reverse("profiles:delete_avatar")).status_code, 405)

    def test_public_page_uses_versioned_image_urls(self):
        self.upload("avatar")
        self.upload("cover")
        self.user.username, self.user.profile_public = "imguser", True
        self.user.save()
        self.user.refresh_from_db()
        page = self.client_class().get(reverse("profiles:detail", args=["imguser"]))
        self.assertContains(page, self.user.avatar_url)
        self.assertContains(page, self.user.cover_url)

    def test_navigation_avatar_is_rendered(self):
        self.upload("avatar")
        self.user.refresh_from_db()
        self.assertContains(self.client.get(reverse("dashboard:buyer_profile")), self.user.avatar_url)
