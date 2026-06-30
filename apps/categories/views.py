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
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'id'

    def list(self, request, *args, **kwargs):
        cached_data = cache.get(CACHE_KEY_CATEGORIES_LIST)
        if cached_data is not None:
            return Response(cached_data)

        # Query database if not cached
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Cache categories list for 24 hours (86400 seconds)
        cache.set(CACHE_KEY_CATEGORIES_LIST, data, 86400)
        return Response(data)

    def perform_create(self, serializer):
        serializer.save()
        # Invalidate categories cache
        cache.delete(CACHE_KEY_CATEGORIES_LIST)

    def perform_update(self, serializer):
        serializer.save()
        # Invalidate categories cache
        cache.delete(CACHE_KEY_CATEGORIES_LIST)

    def perform_destroy(self, instance):
        instance.delete()
        # Invalidate categories cache
        cache.delete(CACHE_KEY_CATEGORIES_LIST)
