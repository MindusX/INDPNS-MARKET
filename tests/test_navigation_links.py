"""Liens de navigation : vérification d'identité et moyens de paiement visibles dans les DEUX barres latérales
(barre de bureau + menu ☰ mobile), et plus d'icône clair/sombre dans les barres horizontales du haut."""
import re

from django.test import TestCase
from django.urls import reverse

from .conftest_helpers import make_seller, make_user, seed


def segment(html, start, end):
    m = re.search(re.escape(start) + r".*?" + re.escape(end), html, re.S)
    return m.group(0) if m else ""


class SellerLinksTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.user = make_seller("seller@example.com")
        self.client.force_login(self.user)
        self.methods = reverse("dashboard:seller_payout_methods")
        self.verif = reverse("dashboard:seller_verification")

    def html(self, name):
        return self.client.get(reverse(name)).content.decode()

    def test_both_links_in_desktop_sidebar_and_mobile_drawer(self):
        html = self.html("dashboard:seller_home")
        for url in (self.methods, self.verif):
            self.assertGreaterEqual(html.count(f'href="{url}"'), 2, url)          # barre de bureau + menu ☰
        self.assertIn('class="side-link', segment(html, '<aside class="sidebar"', "</aside>"))
        self.assertIn(self.methods, segment(html, '<aside class="sidebar"', "</aside>"))
        self.assertIn(self.verif, segment(html, 'id="app-sidebar"', "</aside>"))
        self.assertIn(self.methods, segment(html, 'id="app-sidebar"', "</aside>"))

    def test_seller_in_buyer_space_still_finds_the_links(self):
        html = self.html("dashboard:buyer_home")
        for url in (self.methods, self.verif):
            self.assertGreaterEqual(html.count(f'href="{url}"'), 2, url)

    def test_buyer_without_shop_does_not_see_seller_links(self):
        buyer = self.client_class()
        buyer.force_login(make_user("buyer@example.com"))
        html = buyer.get(reverse("dashboard:buyer_home")).content.decode()
        self.assertNotIn(self.methods, html)
        self.assertNotIn(self.verif, html)

    def test_action_banner_until_identity_is_verified(self):
        html = self.html("dashboard:seller_home")
        self.assertIn("sb-alert", html)
        self.assertIn("Action needed", html)
        self.user.shop.kyc_status = "verified"
        self.user.shop.save()
        html = self.html("dashboard:seller_home")
        self.assertNotIn("sb-alert", html)
        self.assertNotIn("Action needed", html)


class AdminLinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_admin_sees_identity_checks_in_both_sidebars(self):
        admin = make_user("admin@example.com", role="admin")
        self.client.force_login(admin)
        url = reverse("dashboard:admin_kyc")
        html = self.client.get(reverse("dashboard:admin_home")).content.decode()
        self.assertGreaterEqual(html.count(f'href="{url}"'), 2)

    def test_plain_buyer_never_sees_admin_link(self):
        self.client.force_login(make_user("buyer@example.com"))
        self.assertNotIn(reverse("dashboard:admin_kyc"), self.client.get(reverse("dashboard:buyer_home")).content.decode())


class ThemeToggleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_no_theme_toggle_in_dashboard_top_bar_but_kept_in_menu(self):
        self.client.force_login(make_user("u@example.com"))
        html = self.client.get(reverse("dashboard:buyer_home")).content.decode()
        self.assertNotIn("data-theme-toggle", segment(html, '<header class="topbar">', "</header>"))
        self.assertEqual(html.count("data-theme-toggle"), 1)                        # reste accessible dans le menu ☰

    def test_no_theme_toggle_in_auth_top_bar(self):
        html = self.client.get(reverse("accounts:login")).content.decode()
        self.assertNotIn("data-theme-toggle", segment(html, '<header class="auth-top">', "</header>"))
        self.assertIn("data-theme-toggle", html)                                    # toujours dans le menu et le pied de page
