from rest_framework import serializers
from .models import Order, OrderItem
from products.models import Product

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    seller_shop = serializers.ReadOnlyField(source='product.seller.shop_name')

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'seller_shop', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    buyer_name = serializers.ReadOnlyField(source='buyer.username')
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'buyer', 'buyer_name', 'total_amount', 'status', 'items', 'payment_method', 'created_at']
        read_only_fields = ['id', 'buyer', 'buyer_name', 'status', 'created_at']

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
        request = self.context.get('request')
        buyer = request.user
        
        total_amount = validated_data.get('total_amount', 0)
        
        order = Order.objects.create(buyer=buyer, total_amount=total_amount)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order
