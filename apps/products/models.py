import uuid
from django.db import models
from core.models import BaseModel
from django.contrib.auth import get_user_model
from categories.models import Category
from seller.models import SellerProfile

User = get_user_model()

class Product(BaseModel):
    APPROVAL_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name="products", null=True, blank=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    sku = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    description = models.TextField(blank=True, null=True)
    seo_title = models.CharField(max_length=255, blank=True, null=True)
    seo_description = models.TextField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)  # Comma separated tags
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    # Digital Product Fields
    is_digital = models.BooleanField(default=False)
    digital_file = models.FileField(upload_to="digital_products/", blank=True, null=True)
    digital_file_url = models.URLField(blank=True, null=True)
    license_keys = models.TextField(blank=True, null=True, help_text="New-line separated pre-generated keys")

    # Workflow & Publishing Fields
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='approved')
    publish_at = models.DateTimeField(null=True, blank=True)

    # Translation Fields
    name_bn = models.CharField(max_length=255, blank=True, null=True)
    description_bn = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class ProductLicenseKey(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="licenses")
    key = models.CharField(max_length=255)
    is_assigned = models.BooleanField(default=False)
    # Points to OrderItem inside apps/orders/models.py
    # We use a string reference 'orders.OrderItem' to avoid circular import issues
    assigned_to_order_item = models.OneToOneField(
        'orders.OrderItem', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="license_key"
    )

    def __str__(self):
        return f"{self.product.name} - {self.key} (Assigned: {self.is_assigned})"


class ProductVersion(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="versions")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changes = models.JSONField()  # Store dictionary of field changes (old -> new values)
    version_number = models.IntegerField(default=1)

    def __str__(self):
        return f"v{self.version_number} of {self.product.name} by {self.changed_by.username if self.changed_by else 'System'}"


class Review(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(default=5)  # 1 to 5
    comment = models.TextField()

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}*)"
