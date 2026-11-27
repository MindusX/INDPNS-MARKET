"""Images de profil : service (GET) et API d'envoi / suppression / cadrage — mêmes routes que Mindus Forge.

    GET    /api/profile/avatar/<id>        GET    /api/profile/cover/<id>          (image JPEG, ETag, cache immuable avec ?v=)
    POST   /api/profile/upload-avatar      POST   /api/profile/upload-cover         (multipart, champ « file »)
    DELETE /api/profile/avatar             DELETE /api/profile/cover
    PUT    /api/profile/cover/position     (JSON {"position_y": 0..100})

Confidentialité (plus stricte que Mindus, qui est un réseau social) : l'image n'est servie que si le profil est PUBLIC,
ou au propriétaire / à l'équipe. Sinon 404 : l'interface affiche alors l'initiale."""
import json
from functools import wraps

from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse, HttpResponseNotModified, JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_safe

from apps.core.ratelimit import ratelimit
from apps.core.services import audit

from .images import process_profile_image
from .models import ProfileImage, User
from .profile_images import remove_image, store_image

WRITE_METHODS = ("POST", "PUT", "DELETE")


def _json(ok, status=200, **extra):
    resp = JsonResponse({"success": ok, **extra}, status=status)
    resp["Cache-Control"] = "no-store"
    return resp


def api_login_required(view):
    @wraps(view)
    def wrapper(request, *a, **kw):
        if not request.user.is_authenticated:
            return _json(False, 401, error=_("Please sign in."))
        return view(request, *a, **kw)
    return wrapper


def _serve(request, user_id, kind):
    owner_row = User.objects.filter(pk=user_id, is_active=True).only("id", "profile_public", "is_staff", f"{kind}_version").first()
    version = getattr(owner_row, f"{kind}_version", 0) if owner_row else 0
    if not owner_row or not version:
        raise Http404
    can_see = request.user.is_authenticated and (request.user.pk == owner_row.pk or request.user.is_staff)
    if not (owner_row.profile_public or can_see):
        raise Http404

    etag = f'"{kind[0]}{owner_row.pk}-{version}"'
    if request.headers.get("If-None-Match") == etag:
        resp = HttpResponseNotModified()
    else:
        img = ProfileImage.objects.filter(user_id=owner_row.pk).only(f"{kind}_data", f"{kind}_mime").first()
        data = getattr(img, f"{kind}_data", None) if img else None
        if not data:
            raise Http404
        resp = HttpResponse(bytes(data), content_type=getattr(img, f"{kind}_mime") or "image/jpeg")
    resp["ETag"] = etag
    # ?v=<version> change à chaque nouvelle image : on peut donc mettre en cache un an, sans jamais voir une ancienne image.
    resp["Cache-Control"] = "private, max-age=31536000, immutable" if request.GET.get("v") else "private, max-age=60"
    resp["Vary"] = "Cookie"
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Content-Security-Policy"] = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"
    return resp


@require_safe
def avatar_image(request, user_id):
    return _serve(request, user_id, "avatar")


@require_safe
def cover_image(request, user_id):
    return _serve(request, user_id, "cover")


def _upload(request, kind):
    f = request.FILES.get("file")
    if f is None:
        return _json(False, 400, error=_("No file received."))
    try:
        data = process_profile_image(f, kind)
    except ValidationError as exc:
        return _json(False, 400, error=" ".join(exc.messages))
    store_image(request.user, kind, data)
    audit(request.user, f"user.{kind}_updated", request.user, request)
    url = request.user.avatar_url if kind == "avatar" else request.user.cover_url
    return _json(True, url=url, version=getattr(request.user, f"{kind}_version"), position_y=request.user.cover_position_y)


@require_http_methods(["POST"])
@api_login_required
@ratelimit("profile-image", limit=40, window=600, methods=WRITE_METHODS)
def upload_avatar(request):
    return _upload(request, "avatar")


@require_http_methods(["POST"])
@api_login_required
@ratelimit("profile-image", limit=40, window=600, methods=WRITE_METHODS)
def upload_cover(request):
    return _upload(request, "cover")


@require_http_methods(["DELETE"])
@api_login_required
@ratelimit("profile-image", limit=40, window=600, methods=WRITE_METHODS)
def delete_avatar(request):
    remove_image(request.user, "avatar")
    audit(request.user, "user.avatar_removed", request.user, request)
    return _json(True, url="")


@require_http_methods(["DELETE"])
@api_login_required
@ratelimit("profile-image", limit=40, window=600, methods=WRITE_METHODS)
def delete_cover(request):
    remove_image(request.user, "cover")
    audit(request.user, "user.cover_removed", request.user, request)
    return _json(True, url="")


@require_http_methods(["PUT"])
@api_login_required
@ratelimit("profile-image", limit=40, window=600, methods=WRITE_METHODS)
def cover_position(request):
    try:
        value = json.loads(request.body or b"{}").get("position_y")
        value = int(value)
    except (ValueError, TypeError, AttributeError):
        return _json(False, 400, error=_("Invalid position."))
    if not 0 <= value <= 100:
        return _json(False, 400, error=_("Invalid position."))
    if not request.user.cover_version:
        return _json(False, 400, error=_("Upload a cover image first."))
    User.objects.filter(pk=request.user.pk).update(cover_position_y=value)
    request.user.cover_position_y = value
    return _json(True, position_y=value)
