from rest_framework import viewsets, permissions
from .models import Order
from .serializers import OrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Order.objects.none()
            
        queryset = Order.objects.all().select_related('buyer').prefetch_related('items__product__seller', 'transactions')
        if user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
            return queryset
        if hasattr(user, 'role') and user.role == 'seller':
            return queryset.filter(items__product__seller__user=user).distinct()
        return queryset.filter(buyer=user)

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)
