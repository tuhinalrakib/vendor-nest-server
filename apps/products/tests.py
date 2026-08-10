from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from categories.models import Category
from seller.models import SellerProfile
from products.models import Product

User = get_user_model()

class ProductAPITest(TestCase):
    """Test suite for Product model and API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="seller@example.com",
            password="Password123!"
        )
        self.seller = SellerProfile.objects.create(
            user=self.user,
            shop_name="Tech Store",
            subdomain="tech-store"
        )
        self.category = Category.objects.create(
            name="Gadgets",
            slug="gadgets"
        )
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Wireless Mouse",
            slug="wireless-mouse",
            price=25.00,
            stock=100,
            approval_status="approved"
        )

    def test_product_creation(self):
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(self.product.name, "Wireless Mouse")
        self.assertEqual(self.product.price, 25.00)

    def test_product_list_api(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
