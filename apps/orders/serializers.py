from rest_framework import serializers
from .models import Order, OrderItem
from products.models import Product

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    seller_shop = serializers.ReadOnlyField(source='product.seller.shop_name')
    is_digital = serializers.BooleanField(source='product.is_digital', read_only=True)
    digital_file_url = serializers.SerializerMethodField()
    license_key = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'seller_shop', 'quantity', 'price',
            'is_digital', 'digital_file_url', 'license_key'
        ]

    def get_digital_file_url(self, obj):
        if obj.product and obj.product.is_digital:
            if obj.product.digital_file:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.product.digital_file.url)
                return obj.product.digital_file.url
            return obj.product.digital_file_url
        return None

    def get_license_key(self, obj):
        if hasattr(obj, 'license_key') and obj.license_key:
            return obj.license_key.key
        return None

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    buyer_name = serializers.ReadOnlyField(source='buyer.username')
    payment_method = serializers.SerializerMethodField()
    coupon_codes = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Order
        fields = [
            'id', 'buyer', 'buyer_name', 'total_amount', 'status', 'items', 
            'payment_method', 'created_at', 'shipping_name', 'shipping_phone', 
            'shipping_address', 'shipping_city', 'shipping_zip', 'coupon_codes',
            'tracking_number', 'courier_name', 'estimated_delivery'
        ]
        read_only_fields = ['id', 'buyer', 'buyer_name', 'created_at']

    def get_payment_method(self, obj):
        # Prefer direct field on Order (set at COD/payment time)
        if obj.payment_method:
            return obj.get_payment_method_display()
        # Fallback: look up via linked transaction (for existing orders)
        tx = obj.transactions.order_by('-created_at').first()
        if tx:
            return tx.get_payment_method_display()
        return "Not Specified"

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        coupon_codes = validated_data.pop('coupon_codes', [])
        request = self.context.get('request')
        buyer = validated_data.pop('buyer', request.user if request else None)
        
        order = Order.objects.create(buyer=buyer, **validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)

        if coupon_codes and buyer:
            from coupons.models import UserCoupon, Coupon
            from django.utils import timezone
            normalized_codes = [c.strip().upper() for c in coupon_codes]
            for code in normalized_codes:
                try:
                    coupon = Coupon.objects.get(code=code)
                    user_coupon, created = UserCoupon.objects.get_or_create(
                        user=buyer,
                        coupon=coupon,
                        defaults={"is_used": True, "used_at": timezone.now()}
                    )
                    if not created and not user_coupon.is_used:
                        user_coupon.is_used = True
                        user_coupon.used_at = timezone.now()
                        user_coupon.save()
                except Coupon.DoesNotExist:
                    pass

        return order

