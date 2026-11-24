"""Téléchargements : liens signés, temporaires, contrôlés côté serveur. Les fichiers ne sont jamais dans /media/."""
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.core.ratelimit import ratelimit
from apps.core.utils import client_ip
from apps.licenses.models import License
from apps.products.models import ProductVersion

from .models import DownloadLog

SALT = "indpns.download"


def make_token(user, lic, version):
    return signing.dumps({"l": lic.pk, "v": version.pk, "u": user.pk}, salt=SALT)


@login_required
@require_POST
@ratelimit("dlreq", limit=30, window=300)
def request_download(request, license_id, version_id):
    lic = get_object_or_404(License, pk=license_id, buyer=request.user)
    if not lic.is_active:
        raise PermissionDenied
    version = get_object_or_404(ProductVersion, pk=version_id, product=lic.product)
    if not version.is_safe:
        raise Http404
    return redirect("downloads:serve", token=make_token(request.user, lic, version))


@login_required
def serve(request, token):
    try:
        data = signing.loads(token, salt=SALT, max_age=settings.AWS_QUERYSTRING_EXPIRE)
    except signing.BadSignature:
        raise PermissionDenied
    if data["u"] != request.user.pk:
        raise PermissionDenied
    lic = get_object_or_404(License, pk=data["l"], buyer=request.user, revoked_at__isnull=True)
    version = get_object_or_404(ProductVersion, pk=data["v"], product=lic.product)
    if not version.is_safe:
        raise Http404
    DownloadLog.objects.create(license=lic, version=version, ip=client_ip(request))
    if settings.S3_ENABLED:
        return HttpResponseRedirect(version.file.url)   # URL présignée S3, expire après DOWNLOAD_LINK_TTL
    ext = version.file.name.rsplit(".", 1)[-1]
    resp = FileResponse(version.file.open("rb"), as_attachment=True, filename=f"{lic.product.slug}-{version.version}.{ext}")
    resp["Cache-Control"] = "private, no-store"
    return resp
