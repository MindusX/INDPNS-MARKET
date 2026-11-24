def notifications(request):
    u = getattr(request, "user", None)
    if u is not None and u.is_authenticated:
        from .models import Notification
        return {"unread_notifications": Notification.objects.filter(user=u, read_at__isnull=True).count()}
    return {"unread_notifications": 0}
