from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Product, Review

def _invalidate_all_products():
    try:
        cache.incr("products_cache_version")
    except ValueError:
        cache.set("products_cache_version", 1)

@receiver([post_save, post_delete], sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    # Invalidate listing caches via version increment
    _invalidate_all_products()
    
    # Invalidate specific product detail cache
    cache.delete(f"product_detail_{instance.id}")

@receiver([post_save, post_delete], sender=Review)
def invalidate_review_product_cache(sender, instance, **kwargs):
    # Invalidate listing caches via version increment
    _invalidate_all_products()
    
    # Invalidate review product detail cache
    if instance.product:
        cache.delete(f"product_detail_{instance.product.id}")
