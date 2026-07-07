from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Category

@receiver([post_save, post_delete], sender=Category)
def invalidate_categories_cache(sender, instance, **kwargs):
    # Invalidate categories list cache
    cache.delete('categories_list_cache')
    
    # Invalidate specific category detail cache
    cache.delete(f'category_detail_{instance.id}')
    
    # If this category has a parent, invalidate parent cache as well
    if instance.parent:
        cache.delete(f'category_detail_{instance.parent.id}')
