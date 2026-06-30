from rest_framework import serializers
from .models import SellerProfile

class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        fields = [
            "id",
            "shop_name",
            "subdomain",
            "support_email",
            "shop_description",
            "business_license",
            "tax_id",
            "status",
            "rejection_reason",
            "stripe_account_id",
            "stripe_connected",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "rejection_reason", "created_at", "updated_at"]


class AdminSellerProfileSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SellerProfile
        fields = [
            "id",
            "owner_name",
            "email",
            "shop_name",
            "subdomain",
            "support_email",
            "shop_description",
            "business_license",
            "tax_id",
            "status",
            "rejection_reason",
            "stripe_account_id",
            "stripe_connected",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner_name", "email", "created_at", "updated_at"]

