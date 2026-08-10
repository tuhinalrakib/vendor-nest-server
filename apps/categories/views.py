from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.core.cache import cache
from .models import Category
from .serializers import CategorySerializer
from .permissions import IsAdminOrReadOnly

CACHE_KEY_CATEGORIES_LIST = 'categories_list_cache'

class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category model.
    Allows listing and retrieving categories for all authenticated/unauthenticated users.
    Restricts creating, updating, and deleting categories to platform admins.
    Caches the list output in Redis/Cache and invalidates it on write operations.
    """
    from django.db.models import Count
    queryset = Category.objects.select_related('parent').annotate(product_count_annotated=Count('products')).all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'id'
    def list(self, request, *args, **kwargs):
        cached_data = cache.get(CACHE_KEY_CATEGORIES_LIST)
        if cached_data:
            return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(CACHE_KEY_CATEGORIES_LIST, data, 86400)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        category_id = kwargs.get('id')
        if not category_id:
            return super().retrieve(request, *args, **kwargs)

        cache_key = f"category_detail_{category_id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, 86400)
        return response

    def perform_create(self, serializer):
        super().perform_create(serializer)
        from .signals import invalidate_categories_cache
        invalidate_categories_cache(sender=Category, instance=serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        from .signals import invalidate_categories_cache
        invalidate_categories_cache(sender=Category, instance=serializer.instance)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        from .signals import invalidate_categories_cache
        invalidate_categories_cache(sender=Category, instance=instance)
