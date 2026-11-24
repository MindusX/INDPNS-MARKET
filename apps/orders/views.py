from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.ratelimit import ratelimit
from apps.payments.registry import payments_enabled
from apps.payments.services import PaymentError, start_checkout
from apps.products.models import Product

from .services import OrderError, complete_free_order, create_order


@login_required
@require_POST
@ratelimit("checkout", limit=20, window=300)
def checkout(request, slug):
    product = get_object_or_404(Product.objects.public(), slug=slug)
    code = request.POST.get("license", "personal")
    try:
        order = create_order(request.user, product, code)
    except OrderError as e:
        messages.error(request, str(e))
        return redirect(product.get_absolute_url())
    if order.total == 0:
        complete_free_order(order)
        messages.success(request, _("Added to your library."))
        return redirect("dashboard:buyer_library")
    if not payments_enabled():
        messages.error(request, _("Payments are not enabled yet on this marketplace. You can browse, but not buy paid products."))
        return redirect(product.get_absolute_url())
    try:
        url = start_checkout(order, request)
    except PaymentError as e:
        messages.error(request, str(e))
        return redirect(product.get_absolute_url())
    return redirect(url)
