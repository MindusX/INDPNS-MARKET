"""Vérification d'identité (KYC) : page vendeur + file de revue et consultation sécurisée des documents côté équipe."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.core.crypto import encryption_available
from apps.core.permissions import seller_required, staff_role_required
from apps.core.ratelimit import ratelimit
from apps.core.services import audit
from apps.sellers import kyc
from apps.sellers.kyc_forms import IdentityForm
from apps.sellers.models import IdentityVerification, KycDocument

from .navigation import context
from .views import paginate


@seller_required
@ratelimit("kyc-submit", limit=12, window=3600)
def seller_verification(request):
    shop = request.user.shop
    can_submit = kyc.can_submit(shop)
    form = None
    if request.method == "POST":
        action = request.POST.get("action", "identity")
        if action == "shop_verification":            # badge « boutique vérifiée » (comportement historique)
            if shop.verification_status in ("none", "rejected"):
                shop.verification_status = "pending"
                shop.save(update_fields=["verification_status"])
                audit(request.user, "seller.verification_requested", shop, request)
                messages.success(request, _("Verification requested."))
            return redirect("dashboard:seller_verification")
        if not can_submit:
            messages.error(request, _("You cannot submit a new request right now."))
            return redirect("dashboard:seller_verification")
        form = IdentityForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                kyc.submit_verification(shop, form.verification_data(), form.images, request)
            except kyc.KycError as e:
                messages.error(request, str(e))
            else:
                messages.success(request, _("Your documents were sent. We will review them shortly."))
                return redirect("dashboard:seller_verification")
        else:
            messages.error(request, _("Please fix the highlighted fields."))
    if form is None and can_submit:
        form = IdentityForm(initial={"country": shop.country, "nationality": shop.country, "doc_country": shop.country})
    return render(request, "dashboard/seller/verification.html", context(
        request, "seller", shop=shop, form=form, latest=shop.identity_checks.first(), can_submit=can_submit,
        kyc_available=encryption_available()))


# ------------------------------------------------------------------ côté équipe (administrateurs)
@staff_role_required("admin")
def admin_kyc(request):
    status = request.GET.get("status", "pending")
    qs = IdentityVerification.objects.select_related("shop", "shop__user")
    if status in ("pending", "approved", "rejected"):
        qs = qs.filter(status=status)
    return render(request, "dashboard/admin/kyc_list.html", context(request, "admin", page=paginate(request, qs), status=status))


@staff_role_required("admin")
def admin_kyc_detail(request, pk):
    v = get_object_or_404(IdentityVerification.objects.select_related("shop", "shop__user", "reviewed_by").prefetch_related("documents"), pk=pk)
    if v.shop.user_id == request.user.pk:
        raise PermissionDenied                       # on ne valide jamais son propre dossier
    if request.method == "POST":
        try:
            if request.POST.get("action") == "approve":
                kyc.approve(v.pk, request.user, request)
                messages.success(request, _("Identity verified."))
            elif request.POST.get("action") == "reject":
                kyc.reject(v.pk, request.user, request.POST.get("reason", ""), request)
                messages.success(request, _("Request rejected. The seller was notified."))
        except kyc.KycError as e:
            messages.error(request, str(e))
            return redirect("dashboard:admin_kyc_detail", pk=v.pk)
        return redirect("dashboard:admin_kyc")
    audit(request.user, "kyc.viewed", v, request)
    return render(request, "dashboard/admin/kyc_detail.html", context(request, "admin", v=v, documents={d.kind: d for d in v.documents.all()}))


@staff_role_required("admin")
def admin_kyc_document(request, pk, doc_id):
    """Image d'une pièce d'identité : déchiffrée à la volée, jamais mise en cache, chaque consultation est journalisée."""
    doc = get_object_or_404(KycDocument.objects.select_related("verification__shop"), pk=doc_id, verification_id=pk)
    if doc.verification.shop.user_id == request.user.pk:
        raise PermissionDenied
    try:
        data = kyc.document_bytes(doc)
    except kyc.KycError:
        return HttpResponse(status=410)
    audit(request.user, "kyc.document_viewed", doc.verification, request, kind=doc.kind)
    resp = HttpResponse(data, content_type=doc.mime or "image/jpeg")
    resp["Cache-Control"] = "no-store, private, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Content-Security-Policy"] = "default-src 'none'; img-src 'self' data:; sandbox"
    resp["Content-Disposition"] = "inline"
    return resp
