import os
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Avg, Count, Q
from django.urls import reverse

from apps.core.storage import private_storage


def version_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"products/{instance.product.shop_id}/{instance.product_id}/{uuid.uuid4().hex}{ext}"


def cover_upload_to(instance, filename):
    return f"covers/{instance.shop_id}/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"


def gallery_upload_to(instance, filename):
    return f"gallery/{instance.product_id}/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"


class ProductQuerySet(models.QuerySet):
    def public(self):
        return self.filter(status="approved", shop__is_active=True)

    def with_stats(self):
        return self.annotate(
            avg_rating=Avg("reviews__rating", filter=Q(reviews__is_visible=True)),
            review_count=Count("reviews", filter=Q(reviews__is_visible=True), distinct=True),
            sales_count=Count("order_items", filter=Q(order_items__order__status="paid"), distinct=True),
        )


class Product(models.Model):
    STATUS = [("draft", "Draft"), ("pending", "Pending"), ("approved", "Approved"),
              ("rejected", "Rejected"), ("suspended", "Suspended"), ("archived", "Archived")]

    shop = models.ForeignKey("sellers.Shop", on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, max_length=70)
    summary = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    documentation = models.TextField(blank=True)
    category = models.ForeignKey("catalog.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    technologies = models.ManyToManyField("catalog.Technology", blank=True, related_name="products")
    compatibility = models.CharField(max_length=200, blank=True)
    demo_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    cover = models.ImageField(upload_to=cover_upload_to, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), db_index=True)
    status = models.CharField(max_length=10, choices=STATUS, default="draft", db_index=True)
    rejection_reason = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-published_at"])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("products:detail", args=[self.slug])

    @property
    def is_free(self):
        return self.base_price == 0

    def latest_safe_version(self):
        return next((v for v in self.versions.all() if v.is_safe), None)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=gallery_upload_to)
    caption = models.CharField(max_length=120, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class ProductVersion(models.Model):
    SCAN = [("pending", "Pending"), ("clean", "Clean"), ("infected", "Infected"),
            ("skipped", "Skipped (no antivirus configured)"), ("error", "Scan error")]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=30)
    changelog = models.TextField(blank=True)
    file = models.FileField(upload_to=version_upload_to, storage=private_storage, max_length=300)
    file_size = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    scan_status = models.CharField(max_length=10, choices=SCAN, default="pending")
    scan_detail = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.title} v{self.version}"

    @property
    def is_safe(self):
        if self.scan_status == "clean":
            return True
        return self.scan_status == "skipped" and not settings.ANTIVIRUS_REQUIRED


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]


class ProductReport(models.Model):
    REASONS = [("copyright", "Copyright / IP"), ("malware", "Malware or unsafe content"),
               ("misleading", "Misleading description"), ("illegal", "Illegal content"), ("other", "Other")]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=20, choices=REASONS)
    details = models.TextField(max_length=2000, blank=True)
    status = models.CharField(max_length=10, default="open", choices=[("open", "Open"), ("closed", "Closed")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
