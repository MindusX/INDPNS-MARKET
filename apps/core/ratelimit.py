"""Limiteur de débit minimal basé sur le cache (Redis en production)."""
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse

from .utils import client_ip


def hit(key, limit, window):
    """Incrémente et retourne True si la limite est dépassée."""
    cache.add(key, 0, timeout=window)
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        n = 1
    return n > limit


def ratelimit(name, limit=20, window=60, methods=("POST",)):
    def deco(view):
        @wraps(view)
        def wrapper(request, *a, **kw):
            if request.method in methods and hit(f"rl:{name}:{client_ip(request)}", limit, window):
                return HttpResponse("Too many requests. Please slow down.", status=429)
            return view(request, *a, **kw)
        return wrapper
    return deco
