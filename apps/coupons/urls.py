from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CouponViewSet, CouponValidationView

router = DefaultRouter()
router.register(r'', CouponViewSet)

urlpatterns = [
    path('validate/', CouponValidationView.as_view(), name='coupon-validation'),
    path('', include(router.urls)),
]
