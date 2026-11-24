from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    shop = serializers.CharField(source="shop.name", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True, default=None)
    rating = serializers.FloatField(source="avg_rating", read_only=True, default=None)
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "title", "slug", "summary", "category", "shop", "base_price", "rating", "published_at", "url"]
