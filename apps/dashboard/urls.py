from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views as v
from . import views_connect as vc
from . import views_kyc as vk

app_name = "dashboard"

urlpatterns = [
    path("", v.home, name="home"),
    path("theme/", v.set_theme, name="set_theme"),
    # buyer
    path("buyer/", v.buyer_home, name="buyer_home"),
    path("buyer/library/", v.buyer_library, name="buyer_library"),
    path("buyer/orders/", v.buyer_orders, name="buyer_orders"),
    path("buyer/orders/<str:number>/", v.buyer_order, name="buyer_order"),
    path("buyer/favorites/", v.buyer_favorites, name="buyer_favorites"),
    path("buyer/reviews/", v.buyer_reviews, name="buyer_reviews"),
    path("buyer/notifications/", v.buyer_notifications, name="buyer_notifications"),
    path("buyer/security/", v.buyer_security, name="buyer_security"),
    path("buyer/profile/", v.buyer_profile, name="buyer_profile"),
    path("buyer/password/", auth_views.PasswordChangeView.as_view(template_name="dashboard/buyer/password_change.html",
         success_url=reverse_lazy("dashboard:buyer_security")), name="password_change"),
    # seller
    path("seller/", v.seller_home, name="seller_home"),
    path("seller/shop/", v.seller_shop, name="seller_shop"),
    path("seller/products/", v.seller_products, name="seller_products"),
    path("seller/products/new/", v.product_new, name="product_new"),
    path("seller/products/<int:pk>/archive/", v.product_archive, name="product_archive"),
    path("seller/products/<int:pk>/images/<int:image_id>/delete/", v.product_image_delete, name="product_image_delete"),
    path("seller/products/<int:pk>/edit/", v.product_edit, name="product_edit_start"),
    path("seller/products/<int:pk>/edit/<str:step>/", v.product_edit, name="product_edit"),
    path("seller/sales/", v.seller_sales, name="seller_sales"),
    path("seller/revenue/", v.seller_revenue, name="seller_revenue"),
    path("seller/payouts/", v.seller_payouts, name="seller_payouts"),
    path("seller/reviews/", v.seller_reviews, name="seller_reviews"),
    path("seller/verification/", vk.seller_verification, name="seller_verification"),
    path("seller/payout-methods/", vc.seller_payout_methods, name="seller_payout_methods"),
    path("seller/payout-methods/paypal/callback/", vc.seller_paypal_callback, name="seller_paypal_callback"),
    path("seller/payout-methods/stripe/return/", vc.seller_stripe_return, name="seller_stripe_return"),
    path("seller/payout-methods/stripe/refresh/", vc.seller_stripe_refresh, name="seller_stripe_refresh"),
    # admin
    path("admin/", v.admin_home, name="admin_home"),
    path("admin/moderation/", v.admin_moderation, name="admin_moderation"),
    path("admin/moderation/<int:pk>/", v.admin_moderation_detail, name="admin_moderation_detail"),
    path("admin/users/", v.admin_users, name="admin_users"),
    path("admin/orders/", v.admin_orders, name="admin_orders"),
    path("admin/payouts/", v.admin_payouts, name="admin_payouts"),
    path("admin/kyc/", vk.admin_kyc, name="admin_kyc"),
    path("admin/kyc/<int:pk>/", vk.admin_kyc_detail, name="admin_kyc_detail"),
    path("admin/kyc/<int:pk>/document/<int:doc_id>/", vk.admin_kyc_document, name="admin_kyc_document"),
    path("admin/reports/", v.admin_reports, name="admin_reports"),
    path("admin/audit/", v.admin_audit, name="admin_audit"),
]
