from django.contrib import admin
from .models import Coupon

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'seller', 'discount_type', 'discount_value', 'min_purchase', 'expiry_date', 'is_active')
    list_filter = ('is_active', 'discount_type', 'expiry_date', 'seller')
    search_fields = ('code', 'seller__shop_name')
