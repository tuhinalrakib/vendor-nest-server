import uuid
from django.db import models
from core.models import BaseModel
from orders.models import Order
from seller.models import SellerProfile

class Transaction(BaseModel):
    METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('shurjopay', 'Shurjopay'),
        ('cod', 'Cash on Delivery'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Tx {self.id} for Order {self.order.id} ({self.status})"

class Payout(BaseModel):
    METHOD_CHOICES = [
        ('payoneer', 'Payoneer'),
        ('wise', 'Wise'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payout_email_or_account = models.CharField(max_length=255)
    reference_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Payout {self.id} of ${self.amount} to {self.seller.shop_name or self.seller.user.username} ({self.status})"

class PayoutSettings(BaseModel):
    seller = models.OneToOneField(SellerProfile, on_delete=models.CASCADE, related_name="payout_settings")
    payoneer_email = models.EmailField(blank=True, null=True)
    wise_recipient_name = models.CharField(max_length=255, blank=True, null=True)
    wise_iban_or_account = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Payout settings for {self.seller.shop_name or self.seller.user.username}"
