from django.http import JsonResponse
from dashboard.saas_config import SaaSSettings

class MaintenanceModeMiddleware:
    """
    Middleware to intercept incoming requests and block all write operations
    (POST, PUT, PATCH, DELETE) for non-admin accounts when the platform is
    under scheduled maintenance.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Load SaaS settings configuration
        config = SaaSSettings.load()
        
        # If maintenance mode is enabled
        if config.get("maintenance_mode", False):
            user = request.user
            is_admin = False
            
            # Check if user is authenticated and is admin/superuser/staff
            if user and user.is_authenticated:
                is_admin = (
                    user.is_superuser or 
                    user.is_staff or 
                    getattr(user, 'role', '') == 'admin'
                )

            # If not an administrator and attempting a write operation
            if not is_admin and request.method not in ('GET', 'HEAD', 'OPTIONS'):
                # Bypass authentication & settings routes to allow administrator login/logout
                path = request.path
                allowed_paths = [
                    '/api/users/login/',
                    '/api/users/verify-otp/',
                    '/api/users/resend-otp/',
                    '/api/users/logout/',
                    '/api/users/token/refresh/',
                    '/api/dashboard/settings/',
                ]
                
                # If path is not in bypass list, reject request
                if not any(path.startswith(p) for p in allowed_paths):
                    return JsonResponse(
                        {
                            "error": "The platform is currently under scheduled maintenance. Action paused."
                        },
                        status=503
                    )

        return self.get_response(request)
