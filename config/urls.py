"""
URL configuration for VendorNest config package.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from debug_toolbar.toolbar import debug_toolbar_urls
from core.views import home

schema_view = get_schema_view(
   openapi.Info(
      title="VendorNest - Multi-Vendor E-commerce API",
      default_version='v1',
      description="API documentation for VendorNest multi-vendor e-commerce application",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="eng.tuhin77@gmail.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/categories/', include('categories.urls')),
    path('api/sellers/', include('seller.urls')),
    path('api/products/', include('products.urls')),
    path('api/ai/', include('ai.urls')),
    path('api/coupons/', include('coupons.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/notifications/', include('notifications.urls')),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] + debug_toolbar_urls()

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
