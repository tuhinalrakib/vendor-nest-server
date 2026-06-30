from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CartView

router = DefaultRouter()
router.register(r'', ProductViewSet)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('', include(router.urls)),
]
