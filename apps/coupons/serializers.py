from rest_framework import serializers
from .models import Coupon
from seller.models import SellerProfile

class CouponSerializer(serializers.ModelSerializer):
    seller_shop = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'seller', 'seller_shop', 'discount_type', 
            'discount_value', 'min_purchase', 'expiry_date', 'is_active', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'seller', 'created_at', 'updated_at']

    def get_seller_shop(self, obj):
        return obj.seller.shop_name if obj.seller else "Platform Sitewide"

    def validate_code(self, value):
        return value.strip().upper()

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        if user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
            # Admin can optionally specify a seller id
            seller_id = request.data.get('seller')
            if seller_id:
                try:
                    validated_data['seller'] = SellerProfile.objects.get(id=seller_id)
                except SellerProfile.DoesNotExist:
                    raise serializers.ValidationError({"seller": "Seller profile not found."})
        else:
            # Regular sellers are forced to use their own profile
            try:
                validated_data['seller'] = user.seller_profile
            except SellerProfile.DoesNotExist:
                raise serializers.ValidationError({"detail": "User does not have a seller profile."})

        return super().create(validated_data)
