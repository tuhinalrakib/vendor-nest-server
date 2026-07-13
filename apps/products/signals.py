from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Product, Review, ProductVersion

import time
import decimal

def _invalidate_all_products():
    cache.set("products_cache_version", int(time.time()))

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

@receiver(pre_save, sender=Product)
def track_product_changes(sender, instance, **kwargs):
    if not instance.pk:
        return
        
    try:
        old_instance = Product.objects.get(pk=instance.pk)
    except Product.DoesNotExist:
        return

    changes = {}
    fields_to_track = [
        'name', 'sku', 'price', 'compare_at_price', 
        'stock', 'low_stock_threshold', 'description', 
        'approval_status', 'is_digital', 'publish_at', 
        'name_bn', 'description_bn'
    ]

    for field in fields_to_track:
        old_val = getattr(old_instance, field)
        new_val = getattr(instance, field)

        if isinstance(old_val, decimal.Decimal):
            old_val = float(old_val)
        if isinstance(new_val, decimal.Decimal):
            new_val = float(new_val)

        if hasattr(old_val, 'isoformat'):
            old_val = old_val.isoformat()
        if hasattr(new_val, 'isoformat'):
            new_val = new_val.isoformat()

        if old_val != new_val:
            changes[field] = {
                'old': old_val,
                'new': new_val
            }

    if changes:
        changed_by = getattr(instance, '_changed_by', None)
        latest_version = ProductVersion.objects.filter(product=instance).order_by('-version_number').first()
        next_ver = (latest_version.version_number + 1) if latest_version else 1
        
        ProductVersion.objects.create(
            product=instance,
            changed_by=changed_by,
            changes=changes,
            version_number=next_ver
        )
