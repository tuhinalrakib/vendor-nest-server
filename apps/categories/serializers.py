from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
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
            'slug',
            'description',
            'image',
            'parent_id',
            'parent_name',
            'product_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_product_count(self, obj):
        # Check if products relation exists on the Category instance
        if hasattr(obj, 'products'):
            return obj.products.count()
        return 0
