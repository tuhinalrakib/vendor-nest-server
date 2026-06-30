from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
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
