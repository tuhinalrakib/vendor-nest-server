import uuid
from django.db import models
from core.models import BaseModel
from django.contrib.auth import get_user_model

User = get_user_model()

class Notification(BaseModel):
    NOTIFICATION_TYPES = [
        ('seller_application', 'New Seller Application'),
        ('payout_request', 'New Payout Request'),
        ('product_submission', 'New Product Submission'),
        ('system_alert', 'System Alert'),
        ('general', 'General Notification')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='general')
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} for {self.recipient.username} ({'Read' if self.is_read else 'Unread'})"
