from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import SellerProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_seller_profile(sender, instance, created, **kwargs):
    if created and instance.role == "seller":
        SellerProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_seller_profile(sender, instance, **kwargs):
    if instance.role == "seller":
        if not hasattr(instance, 'seller_profile'):
            SellerProfile.objects.get_or_create(user=instance)

@receiver([post_save, post_delete], sender=SellerProfile)
def invalidate_seller_profile_cache(sender, instance, **kwargs):
    if instance.user:
        cache_key = f"seller_profile_cache_{instance.user.id}"
        cache.delete(cache_key)
