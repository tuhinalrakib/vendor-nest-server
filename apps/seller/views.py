from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.core.cache import cache
from .models import SellerProfile
from .serializers import SellerProfileSerializer

class IsSeller(permissions.BasePermission):
    """
    Allows access only to users with role 'seller'.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == "seller"

class SellerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = SellerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get_object(self):
        user = self.request.user
        # Retrieve or create SellerProfile for the authenticated seller
        profile, created = SellerProfile.objects.get_or_create(user=user)
        return profile

    def retrieve(self, request, *args, **kwargs):
        cache_key = f"seller_profile_cache_{request.user.id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, 86400)  # Cache for 24 hours
        return response

    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache_key = f"seller_profile_cache_{self.request.user.id}"
        cache.delete(cache_key)


from rest_framework import viewsets
from .serializers import AdminSellerProfileSerializer

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to users with role 'admin' or staff status.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', None) == 'admin')
        )

class AdminSellerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = AdminSellerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return SellerProfile.objects.exclude(
            user__role='admin'
        ).exclude(
            user__is_staff=True
        ).exclude(
            user__is_superuser=True
        ).order_by('-created_at')

    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache_key = f"seller_profile_cache_{serializer.instance.user.id}"
        cache.delete(cache_key)

    def perform_destroy(self, instance):
        user_id = instance.user.id
        super().perform_destroy(instance)
        cache_key = f"seller_profile_cache_{user_id}"
        cache.delete(cache_key)
