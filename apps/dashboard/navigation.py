from django.utils.translation import gettext_lazy as _


def _i(url_name, label, icon):
    return {"url_name": url_name, "label": label, "icon": icon}


MENUS = {
    "buyer": [
        _i("dashboard:buyer_home", _("Overview"), "dashboard"),
        _i("dashboard:buyer_library", _("Library & downloads"), "download"),
        _i("dashboard:buyer_orders", _("Orders & invoices"), "receipt"),
        _i("dashboard:buyer_favorites", _("Favorites"), "heart"),
        _i("dashboard:buyer_reviews", _("My reviews"), "star"),
        _i("dashboard:buyer_notifications", _("Notifications"), "bell"),
        _i("dashboard:buyer_security", _("Security"), "shield"),
        _i("dashboard:buyer_profile", _("Profile & settings"), "user"),
    ],
    "seller": [
        _i("dashboard:seller_home", _("Overview"), "dashboard"),
        _i("dashboard:seller_products", _("Products"), "box"),
        _i("dashboard:seller_sales", _("Sales"), "receipt"),
        _i("dashboard:seller_revenue", _("Revenue & commissions"), "wallet"),
        _i("dashboard:seller_payouts", _("Payouts"), "wallet"),
        _i("dashboard:seller_reviews", _("Reviews"), "star"),
        _i("dashboard:seller_shop", _("Shop settings"), "store"),
        _i("dashboard:seller_verification", _("Verification"), "shield"),
    ],
    "admin": [
        _i("dashboard:admin_home", _("Overview"), "dashboard"),
        _i("dashboard:admin_moderation", _("Moderation queue"), "shield"),
        _i("dashboard:admin_users", _("Users"), "users"),
        _i("dashboard:admin_orders", _("Orders & refunds"), "receipt"),
        _i("dashboard:admin_payouts", _("Payouts"), "wallet"),
        _i("dashboard:admin_reports", _("Reports"), "flag"),
        _i("dashboard:admin_audit", _("Audit log"), "file"),
    ],
}


def spaces_for(user):
    s = [("buyer", _("Buyer"), "dashboard:buyer_home")]
    if user.is_seller:
        s.append(("seller", _("Seller"), "dashboard:seller_home"))
    if user.is_internal:
        s.append(("admin", _("Admin"), "dashboard:admin_home"))
    return s


def context(request, space, **extra):
    ctx = {"space": space, "menu": MENUS[space], "spaces": spaces_for(request.user),
           "current_view": request.resolver_match.view_name if request.resolver_match else ""}
    ctx.update(extra)
    return ctx
