import time
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Coupon

def clear_coupons_cache(instance_id=None):
    # 1. Update the cache version to current timestamp to invalidate all versioned list caches
    cache.set("coupons_cache_version", int(time.time()))
    
    # 2. Delete specific coupon detail cache
    if instance_id:
        cache.delete(f"coupon_detail_{instance_id}")

@receiver([post_save, post_delete], sender=Coupon)
def invalidate_coupons_cache(sender, instance, **kwargs):
    clear_coupons_cache(instance.id)
