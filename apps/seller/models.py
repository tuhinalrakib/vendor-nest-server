import uuid
from django.db import models
from core.models import BaseModel
from django.contrib.auth import get_user_model

User = get_user_model()

class SellerProfile(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Pending Verification"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("suspended", "Suspended"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="seller_profile"
    )
    shop_name = models.CharField(max_length=255, blank=True, null=True)
    subdomain = models.CharField(max_length=100, unique=True, blank=True, null=True)
    support_email = models.EmailField(blank=True, null=True)
    shop_description = models.TextField(blank=True, null=True)
    business_license = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    rejection_reason = models.TextField(blank=True, null=True)
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_connected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.shop_name or self.user.get_full_name()} - {self.status}"

