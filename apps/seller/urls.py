from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SellerProfileView, AdminSellerProfileViewSet

router = DefaultRouter()
router.register(r"admin-sellers", AdminSellerProfileViewSet, basename="admin-sellers")

urlpatterns = [
    path("profile/", SellerProfileView.as_view(), name="seller-profile"),
    path("", include(router.urls)),
]
