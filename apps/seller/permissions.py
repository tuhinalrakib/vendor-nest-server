from rest_framework import permissions

class IsApprovedSeller(permissions.BasePermission):
    """
    Allows access only to authenticated sellers whose profile is approved.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == "seller"):
            return False
        
        # Check if they have a SellerProfile and its status is 'approved'
        seller_profile = getattr(user, "seller_profile", None)
        return seller_profile is not None and seller_profile.status == "approved"
