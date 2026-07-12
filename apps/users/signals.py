import os
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.cache import cache
from .models.user import UserProfile
from seller.models import SellerProfile

User = get_user_model()

@receiver([post_save, post_delete], sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    # Invalidate global list cache
    cache.delete('users_list_cache')
    # Invalidate individual profile cache
    cache.delete(f"user_profile_cache_{instance.id}")

@receiver([post_save, post_delete], sender=UserProfile)
def invalidate_user_profile_cache(sender, instance, **kwargs):
    # Invalidate global list cache
    cache.delete('users_list_cache')
    # Invalidate individual profile cache
    if instance.user:
        cache.delete(f"user_profile_cache_{instance.user.id}")

@receiver([post_save, post_delete], sender=SellerProfile)
def invalidate_seller_profile_cache(sender, instance, **kwargs):
    # Invalidate global list cache
    cache.delete('users_list_cache')
    # Invalidate individual profile cache
    if instance.user:
        cache.delete(f"user_profile_cache_{instance.user.id}")
        cache.delete(f"seller_profile_cache_{instance.user.id}")


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists, otherwise create it
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def send_verification_email(sender, instance, created, **kwargs):
    if created and not instance.is_email_verified:
        token = default_token_generator.make_token(instance)
        uid = urlsafe_base64_encode(force_bytes(instance.pk))
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        activation_link = f"{frontend_url}/verify-email?uid={uid}&token={token}"
        
        subject = "Verify your email - VendorNest"
        message = f"Hello {instance.get_full_name()},\n\nPlease verify your email by clicking the link below:\n{activation_link}\n\nThank you!"
        
        import threading
        import logging
        logger = logging.getLogger(__name__)

        def run_send_mail():
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [instance.email],
                    fail_silently=False,
                )
                logger.info(f"Verification email successfully sent to {instance.email}")
            except Exception as e:
                logger.error(f"Failed to send email verification to {instance.email}: {e}")

        # Send email in a separate daemon thread to avoid blocking the main server request-response thread
        threading.Thread(target=run_send_mail, daemon=True).start()

