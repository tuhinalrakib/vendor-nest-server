from rest_framework import serializers
from .models import Category

class HybridImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith(('http://', 'https://')):
            return data
        return super().to_internal_value(data)

    def to_representation(self, value):
        if not value:
            return None
        if isinstance(value, str) and value.startswith(('http://', 'https://')):
            return value
        if hasattr(value, 'name') and isinstance(value.name, str) and value.name.startswith(('http://', 'https://')):
            return value.name
        return super().to_representation(value)

class CategorySerializer(serializers.ModelSerializer):
    image = HybridImageField(required=False, allow_null=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='parent',
        write_only=True,
        required=False,
        allow_null=True
    )
    parent_name = serializers.CharField(
        source='parent.name',
        read_only=True
    )
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'name_bn',
            'slug',
            'description',
            'description_bn',
            'image',
            'parent_id',
            'parent_name',
            'product_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_product_count(self, obj):
        # Use annotated value if available to prevent N+1 queries
        if hasattr(obj, 'product_count_annotated'):
            return obj.product_count_annotated
        # Fallback check if products relation exists on the Category instance
        if hasattr(obj, 'products'):
            return obj.products.count()
        return 0
