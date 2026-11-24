from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.sessions.models import Session
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.ratelimit import ratelimit
from apps.core.services import audit

from .forms import LoginForm, RegisterForm
from .models import User, UserSession
from .services import send_verification_email
from .tokens import read_verify_token


@ratelimit("register", limit=10, window=3600)
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        send_verification_email(user, request)
        audit(user, "user.registered", user, request)
        request.session["verify_email"] = user.email
        return redirect("accounts:verify_sent")
    return render(request, "auth/register.html", {"form": form})


def verify_sent(request):
    return render(request, "auth/verify_sent.html", {"email": request.session.get("verify_email", "")})


@ratelimit("resend", limit=5, window=3600)
@require_POST
def resend_verification(request):
    email = (request.POST.get("email") or request.session.get("verify_email") or "").lower().strip()
    user = User.objects.filter(email=email, email_verified=False).first()
    if user:
        send_verification_email(user, request)
    messages.success(request, _("If this address needs confirmation, a new email has been sent."))
    return redirect("accounts:verify_sent")


def verify(request, token):
    data = read_verify_token(token)
    user = User.objects.filter(pk=data["uid"], email=data["email"]).first() if data else None
    if not user:
        return render(request, "auth/verify_result.html", {"ok": False}, status=400)
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        audit(user, "user.email_verified", user, request)
    return render(request, "auth/verify_result.html", {"ok": True})


@method_decorator(ratelimit("login", limit=30, window=300), name="dispatch")
class SignInView(LoginView):
    template_name = "auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        resp = super().form_valid(form)
        lang = self.request.user.preferred_language
        if lang:
            self.request.session["_language"] = lang
        return resp


class SignOutView(LogoutView):
    http_method_names = ["post"]


@login_required
def become_seller(request):
    from apps.sellers.forms import ShopForm
    from apps.sellers.services import create_shop

    if request.user.is_seller:
        return redirect("dashboard:seller_home")
    form = ShopForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        create_shop(request.user, form.cleaned_data)
        audit(request.user, "seller.created", request.user.shop, request)
        messages.success(request, _("Your shop has been created. Complete your profile and publish your first product."))
        return redirect("dashboard:seller_home")
    return render(request, "auth/become_seller.html", {"form": form})


@login_required
@require_POST
def close_other_sessions(request):
    others = UserSession.objects.filter(user=request.user).exclude(session_key=request.session.session_key)
    Session.objects.filter(session_key__in=list(others.values_list("session_key", flat=True))).delete()
    others.delete()
    audit(request.user, "user.sessions_closed", request.user, request)
    messages.success(request, _("All other sessions were closed."))
    return redirect("dashboard:buyer_security")
