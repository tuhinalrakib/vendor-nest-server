import uuid
from django.db import models
from core.models import BaseModel
from django.contrib.auth import get_user_model
from products.models import Product

User = get_user_model()

class Order(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),          # Created, awaiting payment
        ("cod_confirmed", "COD Confirmed"),  # Cash on Delivery — confirmed, pay on delivery
        ("paid", "Paid"),                # Online payment completed
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("stripe", "Stripe"),
        ("shurjopay", "Shurjopay"),
        ("cod", "Cash on Delivery"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    stock_deducted = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # We need to save the order first to ensure it has an ID and items can be accessed,
        # but wait, items are added after the order is created. 
        # So at creation, there are no items. 
        # We should check the status, save the order, and then if it's a qualifying status 
        # and stock_deducted is False, we deduct stock.
        super().save(*args, **kwargs)
        
        if self.status in ["paid", "delivered", "cod_confirmed"]:
            stock_updated = False
            
            if not self.stock_deducted:
                for item in self.items.all():
                    if item.product:
                        item.product.stock = max(0, item.product.stock - item.quantity)
                        item.product.save()
                stock_updated = True
                
            email_updated = False
            if not self.email_sent:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    subject = f"Order Confirmed - VendorNest [Order #{self.id}]"
                    message = f"""Hello {self.buyer.username},

Your order #{self.id} has been successfully confirmed. 
Total Amount: ${self.total_amount}
Payment Method: {self.get_payment_method_display() if self.payment_method else self.get_status_display()}

You can view your order details and download your Invoice PDF from your dashboard:
http://localhost:3000/orders

Thank you for shopping with VendorNest!
"""
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vendornest.com',
                        [self.buyer.email],
                        fail_silently=True,
                    )
                    email_updated = True
                except Exception as e:
                    print(f"Failed to send order confirmation email: {e}")
            
            # Update tracked states without calling save() recursively
            if stock_updated or email_updated:
                Order.objects.filter(pk=self.pk).update(
                    stock_deducted=True if stock_updated else self.stock_deducted,
                    email_sent=True if email_updated else self.email_sent
                )

    def __str__(self):
        return f"Order {self.id} by {self.buyer.username}"

class OrderItem(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="order_items")
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"
