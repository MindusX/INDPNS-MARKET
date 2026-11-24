from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """API publique en lecture seule : uniquement les produits approuvés."""
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        qs = Product.objects.public().with_stats().select_related("shop", "category").order_by("-published_at")
        q = self.request.query_params.get("q")
        cat = self.request.query_params.get("category")
        if q:
            qs = qs.filter(title__icontains=q)
        if cat:
            qs = qs.filter(category__slug=cat)
        return qs
