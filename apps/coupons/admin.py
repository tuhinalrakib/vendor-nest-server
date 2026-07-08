from django.contrib import admin
from .models import Coupon, UserCoupon

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'seller', 'discount_type', 'discount_value', 'min_purchase', 'expiry_date', 'is_active')
    list_filter = ('is_active', 'discount_type', 'expiry_date', 'seller')
    search_fields = ('code', 'seller__shop_name')

@admin.register(UserCoupon)
class UserCouponAdmin(admin.ModelAdmin):
    list_display = ('user', 'coupon', 'is_used', 'used_at', 'saved_at')
    list_filter = ('is_used', 'saved_at', 'used_at')
    search_fields = ('user__email', 'coupon__code')

