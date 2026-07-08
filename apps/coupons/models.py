import uuid
from django.db import models
from core.models import BaseModel
from seller.models import SellerProfile

class Coupon(BaseModel):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name="coupons",
        null=True,
        blank=True
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percentage'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.discount_value} ({self.discount_type})"


class UserCoupon(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name="saved_coupons"
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name="users_saved"
    )
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'coupon')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.email} - {self.coupon.code} (Used: {self.is_used})"

