from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("verify/sent/", views.verify_sent, name="verify_sent"),
    path("verify/resend/", views.resend_verification, name="resend_verification"),
    path("verify/<str:token>/", views.verify, name="verify"),
    path("become-seller/", views.become_seller, name="become_seller"),
    path("sessions/close-others/", views.close_other_sessions, name="close_other_sessions"),
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="auth/password_reset_form.html", email_template_name="emails/password_reset.txt",
        html_email_template_name="emails/password_reset.html", subject_template_name="emails/password_reset_subject.txt",
        success_url=reverse_lazy("accounts:password_reset_done")), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="auth/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="auth/password_reset_confirm.html", success_url=reverse_lazy("accounts:password_reset_complete")), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="auth/password_reset_complete.html"), name="password_reset_complete"),
]
