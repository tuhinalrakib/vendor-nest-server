from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from unittest.mock import patch
from apps.payments.models import Transaction
from apps.orders.models import Order
from apps.payments.gateways.wise_client import WiseSandboxClient

User = get_user_model()

class SSLCommerzCallbackViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testbuyer", password="password")
        self.order = Order.objects.create(
            buyer=self.user,
            total_amount="250.00",
            shipping_name="John Doe",
            shipping_phone="01700000000",
            shipping_address="Dhaka",
            shipping_city="Dhaka",
            shipping_zip="1212"
        )
        self.tx = Transaction.objects.create(
            order=self.order,
            amount="250.00",
            payment_method='sslcommerz',
            status='pending',
            transaction_id='ssl_test_transaction_id'
        )

    def test_callback_cancel(self):
        # SSLCommerz cancel callback redirects to frontend with cancel query parameters
        url = reverse('sslcommerz-callback') + "?status=cancel"
        response = self.client.get(url)
        expected_redirect = f"{settings.FRONTEND_URL}/checkout?checkout_success=false&payment_status=cancel"
        self.assertRedirects(response, expected_redirect, fetch_redirect_response=False)

    def test_callback_missing_tx_id(self):
        url = reverse('sslcommerz-callback')
        response = self.client.get(url)
        expected_redirect = f"{settings.FRONTEND_URL}/checkout?checkout_success=false&error=missing_transaction_id"
        self.assertRedirects(response, expected_redirect, fetch_redirect_response=False)

    def test_callback_transaction_not_found(self):
        url = reverse('sslcommerz-callback') + "?status=fail&tran_id=NON_EXISTENT_ID"
        response = self.client.get(url)
        expected_redirect = f"{settings.FRONTEND_URL}/checkout?checkout_success=false&payment_status=fail"
        self.assertRedirects(response, expected_redirect, fetch_redirect_response=False)


class WiseSandboxClientTest(TestCase):
    def test_create_recipient_fallback(self):
        with patch('apps.payments.gateways.wise_client.WISE_API_TOKEN', None):
            res = WiseSandboxClient.create_recipient("Jane Doe", "jane@example.com")
            self.assertTrue(res["id"].startswith("rec_sim_"))
            self.assertEqual(res["name"], "Jane Doe")
            self.assertEqual(res["details"], "jane@example.com")

    def test_create_quote_fallback(self):
        with patch('apps.payments.gateways.wise_client.WISE_API_TOKEN', None):
            res = WiseSandboxClient.create_quote("USD", "EUR", "100.00")
            self.assertTrue(res["id"].startswith("qte_sim_"))
            self.assertEqual(res["source"], "USD")
            self.assertEqual(res["target"], "EUR")

    def test_create_transfer_fallback(self):
        with patch('apps.payments.gateways.wise_client.WISE_API_TOKEN', None):
            res = WiseSandboxClient.create_transfer("rec_123", "qte_123", "Payout_Ref")
            self.assertTrue(res["id"].startswith("trf_sim_"))
            self.assertEqual(res["status"], "processing")
