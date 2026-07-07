from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CartView, CloudinarySignatureView

router = DefaultRouter()
router.register(r'', ProductViewSet)

urlpatterns = [
    path('cloudinary-signature/', CloudinarySignatureView.as_view(), name='cloudinary-signature'),
    path('cart/', CartView.as_view(), name='cart'),
    path('', include(router.urls)),
]
