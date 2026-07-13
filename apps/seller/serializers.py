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
            "balance",
            "plan",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "rejection_reason", "balance", "created_at", "updated_at"]

    def validate(self, attrs):
        subdomain = attrs.get('subdomain')
        plan = attrs.get('plan')
        if not plan and self.instance:
            plan = self.instance.plan
        if not plan:
            plan = 'starter'

        if subdomain and plan == 'starter':
            raise serializers.ValidationError({
                "subdomain": "Custom subdomains are only available on Growth and Enterprise plans."
            })
        return attrs


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
            "balance",
            "plan",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner_name", "email", "balance", "created_at", "updated_at"]
