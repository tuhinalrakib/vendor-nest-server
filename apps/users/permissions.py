from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to users with role 'admin', staff status, or superuser status.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (
                request.user.is_staff or 
                request.user.is_superuser or 
                getattr(request.user, "role", None) == "admin"
            )
        )
