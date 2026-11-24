from django.urls import path

from . import views

app_name = "sellers"

urlpatterns = [
    path("pricing/", views.pricing, name="pricing"),
    path("sellers/", views.shop_list, name="list"),
    path("shop/<slug:slug>/", views.shop_detail, name="detail"),
]
