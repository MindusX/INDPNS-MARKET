from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.licenses.models import License

from .forms import ReviewForm
from .models import Review


@login_required
@require_POST
def post_review(request, license_id):
    lic = get_object_or_404(License, pk=license_id, buyer=request.user, revoked_at__isnull=True)
    if Review.objects.filter(user=request.user, product=lic.product).exists():
        messages.error(request, _("You already reviewed this product."))
        return redirect(lic.product.get_absolute_url())
    form = ReviewForm(request.POST)
    if form.is_valid():
        r = form.save(commit=False)
        r.product, r.user, r.license = lic.product, request.user, lic
        r.save()
        messages.success(request, _("Thanks for your review!"))
    else:
        messages.error(request, _("Please choose a rating."))
    return redirect(lic.product.get_absolute_url() + "#reviews")
