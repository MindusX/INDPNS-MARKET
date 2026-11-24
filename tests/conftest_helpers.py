from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.accounts.models import User
from apps.licenses.models import LicenseType, ProductLicensePrice
from apps.products.models import Product, ProductVersion
from apps.sellers.services import create_shop


def seed():
    call_command("seed_initial", verbosity=0)


def make_user(email="u@example.com", password="Str0ng-pass-123!", verified=True, **kw):
    return User.objects.create_user(email, password, display_name=kw.pop("display_name", "Test"), email_verified=verified, **kw)


def make_seller(email="s@example.com"):
    u = make_user(email)
    create_shop(u, {"name": "Shop " + email.split("@")[0]})
    return u


def make_product(seller, price="10.00", status="approved", title="Demo product"):
    from apps.catalog.models import Category
    p = Product.objects.create(shop=seller.shop, title=title, slug=title.lower().replace(" ", "-") + str(Product.objects.count()),
                               summary="s", description="d" * 80, category=Category.objects.first(), status=status)
    lt = LicenseType.objects.get(code="personal")
    ProductLicensePrice.objects.create(product=p, license_type=lt, price=Decimal(price))
    p.base_price = Decimal(price)
    p.save()
    v = ProductVersion(product=p, version="1.0", file=SimpleUploadedFile("a.zip", b"PK\x05\x06" + b"\0" * 18), scan_status="skipped", file_size=22)
    v.save()
    return p
