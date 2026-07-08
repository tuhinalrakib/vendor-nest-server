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
            recipient_email = instance.user.email
            if recipient_email:
                subject = "Your Seller Application has been Approved! - VendorNest"
                message_text = (
                    f"Hello {instance.user.full_name or instance.user.username},\n\n"
                    f"Congratulations! Your seller application for '{instance.shop_name or 'your shop'}' on VendorNest "
                    f"has been approved by our administrators.\n\n"
                    f"You can now access your seller dashboard, manage your store settings, and list products in our catalog.\n"
                    f"Your store subdomain: {instance.subdomain or 'not-set'}.vendornest.com\n\n"
                    f"Thank you for choosing VendorNest!\n\n"
                    f"Best regards,\n"
                    f"The VendorNest Team"
                )
                try:
                    send_mail(
                        subject=subject,
                        message=message_text,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient_email],
                        fail_silently=False,
                    )
                    logger.info(f"Successfully sent approval email to {recipient_email}")
                except Exception as e:
                    logger.error(f"Failed to send approval email to {recipient_email}: {e}")

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
