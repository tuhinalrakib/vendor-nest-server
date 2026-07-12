from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StripeCheckoutSessionView, StripeVerifyView,
    SSLCommerzInitiateView, SSLCommerzCallbackView,
    CODPaymentView, PayoutSettingsView,
    PayoutViewSet, PayoutDisburseView
)

router = DefaultRouter()
router.register(r'payouts', PayoutViewSet, basename='payout')

urlpatterns = [
    # Checkout Payments
    path('stripe/create-checkout-session/', StripeCheckoutSessionView.as_view(), name='stripe-checkout-session'),
    path('stripe/verify/', StripeVerifyView.as_view(), name='stripe-verify'),
    path('sslcommerz/initiate/', SSLCommerzInitiateView.as_view(), name='sslcommerz-initiate'),
    path('sslcommerz/callback/', SSLCommerzCallbackView.as_view(), name='sslcommerz-callback'),
    path('cod/', CODPaymentView.as_view(), name='cod-payment'),

    # Payouts
    path('payout-settings/', PayoutSettingsView.as_view(), name='payout-settings'),
    path('payouts/<uuid:pk>/disburse/', PayoutDisburseView.as_view(), name='payout-disburse'),
    path('', include(router.urls)),
]
