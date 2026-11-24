from django.utils import timezone

from .models import License


def issue_license(order_item):
    lic, _ = License.objects.get_or_create(
        order_item=order_item,
        defaults={"buyer": order_item.order.buyer, "product": order_item.product, "license_type": order_item.license_type},
    )
    return lic


def revoke_license(order_item):
    License.objects.filter(order_item=order_item, revoked_at__isnull=True).update(revoked_at=timezone.now())
