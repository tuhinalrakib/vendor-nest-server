from rest_framework import serializers
from .models import Transaction, Payout, PayoutSettings

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'order', 'amount', 'payment_method', 'status', 'transaction_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class PayoutSerializer(serializers.ModelSerializer):
    seller_shop = serializers.SerializerMethodField()

    class Meta:
        model = Payout
        fields = ['id', 'seller', 'seller_shop', 'amount', 'payout_method', 'status', 'payout_email_or_account', 'reference_id', 'created_at']
        read_only_fields = ['id', 'seller', 'seller_shop', 'status', 'reference_id', 'created_at']

    def get_seller_shop(self, obj):
        return obj.seller.shop_name if obj.seller else "Platform Store"

class PayoutSettingsSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = PayoutSettings
        fields = ['payoneer_email', 'wise_recipient_name', 'wise_iban_or_account', 'balance']

    def get_balance(self, obj):
        return str(obj.seller.balance) if obj.seller else "0.00"
