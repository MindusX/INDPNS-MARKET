from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def staff_role_required(min_role="moderator"):
    """Accès réservé aux rôles internes (moderator < support < admin < superadmin)."""
    def deco(view):
        @wraps(view)
        @login_required
        def wrapper(request, *a, **kw):
            if not request.user.has_role_at_least(min_role):
                raise PermissionDenied
            return view(request, *a, **kw)
        return wrapper
    return deco


def seller_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *a, **kw):
        if not hasattr(request.user, "shop"):
            return redirect("accounts:become_seller")
        return view(request, *a, **kw)
    return wrapper
