from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Coupon

@receiver([post_save, post_delete], sender=Coupon)
def invalidate_coupons_cache(sender, instance, **kwargs):
    # Invalidate listing caches via version increment
    try:
        cache.incr("coupons_cache_version")
    except ValueError:
        cache.set("coupons_cache_version", 1)
        
    # Invalidate specific coupon detail cache
    cache.delete(f"coupon_detail_{instance.id}")
