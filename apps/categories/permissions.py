from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow platform admins to create, update, or delete categories.
    Anyone can view (read-only) the categories.
    """
    def has_permission(self, request, view):
        # Read operations are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write operations are only allowed for authenticated users with 'admin' role or superuser/staff
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'admin' or request.user.is_staff or request.user.is_superuser)
        )
