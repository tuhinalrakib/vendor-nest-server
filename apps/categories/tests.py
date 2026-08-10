from typing import Any
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.core.cache import cache
from categories.models import Category

class CategoryAPITest(TestCase):
    """Test suite for Category model and API endpoints."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics",
            description="Electronic items and gadgets"
        )

    def test_category_creation(self):
        self.assertGreaterEqual(Category.objects.count(), 1)
        self.assertEqual(self.category.name, "Electronics")
        self.assertEqual(str(self.category), "Electronics")

    def test_category_list_api(self):
        response = self.client.get("/api/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data: Any = getattr(response, "data", [])
        self.assertGreaterEqual(len(data), 1)

    def test_category_detail_api(self):
        response = self.client.get(f"/api/categories/{self.category.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data: Any = getattr(response, "data", {})
        self.assertEqual(data["name"], "Electronics")
