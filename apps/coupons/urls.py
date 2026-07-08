from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CouponViewSet, CouponValidationView, SaveCouponView, SavedCouponsView, ApplicableCouponsView

router = DefaultRouter()
router.register(r'', CouponViewSet)

urlpatterns = [
    path('validate/', CouponValidationView.as_view(), name='coupon-validation'),
    path('save/', SaveCouponView.as_view(), name='coupon-save'),
    path('saved/', SavedCouponsView.as_view(), name='coupon-saved'),
    path('applicable/', ApplicableCouponsView.as_view(), name='coupon-applicable'),
    path('', include(router.urls)),
]

