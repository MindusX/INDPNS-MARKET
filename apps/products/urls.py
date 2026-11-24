from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("explore/", views.product_list, name="explore"),
    path("new/", views.product_list, {"preset": "new"}, name="new"),
    path("popular/", views.product_list, {"preset": "popular"}, name="popular"),
    path("top-rated/", views.product_list, {"preset": "top-rated"}, name="top_rated"),
    path("free/", views.product_list, {"preset": "free"}, name="free"),
    path("premium/", views.product_list, {"preset": "premium"}, name="premium"),
    path("search/", views.product_list, name="search"),
    path("category/<slug:category_slug>/", views.product_list, name="category"),
    path("p/<slug:slug>/", views.product_detail, name="detail"),
    path("p/<slug:slug>/favorite/", views.toggle_favorite, name="favorite"),
    path("p/<slug:slug>/report/", views.report_product, name="report"),
]
