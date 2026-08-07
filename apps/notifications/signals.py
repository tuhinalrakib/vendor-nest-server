from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
import logging
from seller.models import SellerProfile
from payments.models import Payout
from .models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=SellerProfile)
def store_original_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            original = SellerProfile.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except SellerProfile.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None

@receiver(post_save, sender=SellerProfile)
def create_seller_application_notification(sender, instance, created, **kwargs):
    # Only notify admins when a new seller application is created with 'pending' status
    if created and instance.status == 'pending':
        admins = User.objects.filter(role='admin', is_active=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title="New Seller Application",
                message=f"Shop '{instance.shop_name or instance.user.get_full_name()}' has applied for seller status.",
                notification_type="seller_application"
            )
    
    # Notify seller on approval and send verification email
    elif not created:
        original_status = getattr(instance, "_original_status", None)
        if original_status != "approved" and instance.status == "approved":
            # 1. Create a notification for the seller
            Notification.objects.create(
                recipient=instance.user,
                title="Seller Application Approved",
                message=f"Congratulations! Your seller application for '{instance.shop_name or 'your shop'}' has been approved. You can now manage your store settings and add products.",
                notification_type="general"
            )
            
            # 2. Send email to the seller
            if instance.user.email:
                from users.utils import send_seller_approval_email
                send_seller_approval_email(instance.user, instance.shop_name, instance.subdomain)

@receiver(post_save, sender=Payout)
def create_payout_request_notification(sender, instance, created, **kwargs):
    # Notify admins when a seller requests a payout
    if created and instance.status == 'pending':
        admins = User.objects.filter(role='admin', is_active=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title="New Payout Request",
                message=f"Shop '{instance.seller.shop_name}' requested a payout of ${instance.amount}.",
                notification_type="payout_request"
            )

from django.db import models
from products.models import Product

@receiver(pre_save, sender=Product)
def store_original_product_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            original = Product.objects.get(pk=instance.pk)
            instance._original_approval_status = original.approval_status
        except Product.DoesNotExist:
            instance._original_approval_status = None
    else:
        instance._original_approval_status = None

@receiver(post_save, sender=Product)
def create_product_submission_notification(sender, instance, created, **kwargs):
    original_status = getattr(instance, "_original_approval_status", None)
    
    # 1. When product is submitted or status becomes 'pending', notify all admins
    if (created and instance.approval_status == 'pending') or (not created and original_status != 'pending' and instance.approval_status == 'pending'):
        shop_name = instance.seller.shop_name if (instance.seller and instance.seller.shop_name) else "A seller"
        admins = User.objects.filter(
            models.Q(role='admin') | models.Q(is_superuser=True) | models.Q(is_staff=True),
            is_active=True
        ).distinct()
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title="New Product Submitted",
                message=f"Shop '{shop_name}' submitted product '{instance.name}' for moderation approval.",
                notification_type="product_submission"
            )
            
    # 2. When admin approves a product, notify the seller
    elif not created and original_status != 'approved' and instance.approval_status == 'approved':
        if instance.seller and instance.seller.user:
            Notification.objects.create(
                recipient=instance.seller.user,
                title="Product Approved",
                message=f"Your product '{instance.name}' has been approved by admin and is now live!",
                notification_type="general"
            )

    # 3. When admin rejects a product, notify the seller
    elif not created and original_status != 'rejected' and instance.approval_status == 'rejected':
        if instance.seller and instance.seller.user:
            Notification.objects.create(
                recipient=instance.seller.user,
                title="Product Rejected / Flagged",
                message=f"Your product '{instance.name}' was rejected/flagged during moderation.",
                notification_type="general"
            )

