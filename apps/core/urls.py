from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("healthz", views.healthz, name="healthz"),
    path("healthz/", views.healthz),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("offline/", views.offline, name="offline"),
    path("download/", views.download_page, name="download"),
    path("contact/", views.contact, name="contact"),
    path("legal/<slug:slug>/", views.legal_page, name="legal"),
    path("about/", views.static_page, {"page": "about"}, name="about"),
    path("mission/", views.static_page, {"page": "mission"}, name="mission"),
    path("help/", views.static_page, {"page": "help"}, name="help"),
    path("faq/", views.static_page, {"page": "faq"}, name="faq"),
    path("docs/", views.static_page, {"page": "docs"}, name="docs"),
    path("how-to-buy/", views.static_page, {"page": "how-to-buy"}, name="how_to_buy"),
    path("how-to-sell/", views.static_page, {"page": "how-to-sell"}, name="how_to_sell"),
    path("license-guide/", views.static_page, {"page": "license-guide"}, name="license_guide"),
    path("affiliate/", views.static_page, {"page": "affiliate"}, name="affiliate"),
]
