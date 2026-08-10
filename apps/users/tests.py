from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class UserModelTest(TestCase):
    """Test user model and manager functionality."""
    def test_create_user_successful(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        self.assertEqual(user.email, "testuser@example.com")
        self.assertTrue(user.check_password("TestPassword123!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser_successful(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!"
        )
        self.assertEqual(admin.email, "admin@example.com")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

class UserAuthAPITest(TestCase):
    """Test authentication endpoints."""
    def setUp(self):
        self.client = APIClient()
        self.register_url = "/api/users/register/"
        self.login_url = "/api/users/login/"

    def test_user_registration(self):
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "full_name": "New User",
            "first_name": "New",
            "last_name": "User"
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
