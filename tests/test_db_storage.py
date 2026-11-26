"""DatabaseStorage : médias publics persistants stockés en base, servis par /media/<nom> (production sans S3)."""
import io

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.core.models import StoredFile
from apps.core.storage import DatabaseStorage


def webp_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), (10, 120, 200)).save(buf, "WEBP")
    return buf.getvalue()


@override_settings(DEBUG=False)
class DatabaseStorageTests(TestCase):
    def setUp(self):
        self.storage = DatabaseStorage()

    def test_save_open_exists_size_delete(self):
        data = webp_bytes()
        name = self.storage.save("profiles/avatars/abc.webp", ContentFile(data))
        self.assertEqual(name, "profiles/avatars/abc.webp")
        self.assertTrue(self.storage.exists(name))
        self.assertEqual(self.storage.size(name), len(data))
        with self.storage.open(name) as f:
            self.assertEqual(f.read(), data)
        self.assertEqual(StoredFile.objects.get(name=name).content_type, "image/webp")
        self.storage.delete(name)
        self.assertFalse(self.storage.exists(name))

    def test_name_collision_does_not_overwrite(self):
        a = self.storage.save("profiles/x.webp", ContentFile(b"one"))
        b = self.storage.save("profiles/x.webp", ContentFile(b"two"))
        self.assertNotEqual(a, b)

    def test_url_uses_media_url(self):
        self.assertEqual(self.storage.url("profiles/avatars/a b.webp"), "/media/profiles/avatars/a%20b.webp")

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.storage.open("nope.webp")


@override_settings(DEBUG=False)
class MediaServingTests(TestCase):
    def setUp(self):
        self.name = DatabaseStorage().save("profiles/avatars/served.webp", ContentFile(webp_bytes()))

    def test_serves_image_with_safe_headers(self):
        r = self.client.get("/media/" + self.name)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/webp")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertIn("sandbox", r["Content-Security-Policy"])
        self.assertIn("immutable", r["Cache-Control"])
        self.assertEqual(r.content, webp_bytes())

    def test_etag_returns_304(self):
        etag = self.client.get("/media/" + self.name)["ETag"]
        self.assertEqual(self.client.get("/media/" + self.name, HTTP_IF_NONE_MATCH=etag).status_code, 304)

    def test_unknown_file_is_404(self):
        self.assertEqual(self.client.get("/media/profiles/avatars/missing.webp").status_code, 404)

    def test_non_image_is_forced_to_download(self):
        n = DatabaseStorage().save("profiles/evil.html", ContentFile(b"<script>alert(1)</script>"))
        r = self.client.get("/media/" + n)
        self.assertEqual(r["Content-Type"], "application/octet-stream")
        self.assertEqual(r["Content-Disposition"], "attachment")

    def test_svg_is_not_served_inline(self):
        n = DatabaseStorage().save("profiles/a.svg", ContentFile(b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"))
        self.assertEqual(self.client.get("/media/" + n)["Content-Type"], "application/octet-stream")

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post("/media/" + self.name).status_code, 405)
