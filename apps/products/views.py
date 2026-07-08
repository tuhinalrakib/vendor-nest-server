from rest_framework.views import APIView
from rest_framework import status
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from django.core.cache import cache
from .models import Product
from .serializers import ProductSerializer
from seller.permissions import IsApprovedSeller

class IsApprovedSellerOrReadOnly(permissions.BasePermission):
    """
    Allow read-only requests for non-sellers or admins.
    Sellers can write (create) if approved, and can update/delete only their own products.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
            
        if not (request.user and request.user.is_authenticated):
            return False
            
        # Admin / Staff
        if request.user.is_staff or request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return True
            
        # Check seller status via IsApprovedSeller permission
        permission = IsApprovedSeller()
        return permission.has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        # Admin / Staff can do anything
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')):
            return True
            
        # Seller can only view, update, delete their own product
        if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'seller':
            return obj.seller.user == request.user
            
        # Safe methods for others (e.g. customers or public)
        if request.method in permissions.SAFE_METHODS:
            return True
            
        return False

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsApprovedSellerOrReadOnly]

    def get_list_cache_key(self, request):
        import hashlib
        import json

        user = request.user
        if not user or not user.is_authenticated:
            base_key = 'products_list_all'
        elif user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
            base_key = 'products_list_all'
        elif hasattr(user, 'role') and user.role == 'seller':
            base_key = f'products_list_seller_{user.id}'
        else:
            base_key = 'products_list_all'

        # Hash query parameters to prevent key collisions for different filters
        query_params = dict(request.query_params.items())
        params_str = json.dumps(query_params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode('utf-8')).hexdigest()

        # Retrieve/initialize cache version for products using timestamp
        import time
        cache_version = cache.get_or_set("products_cache_version", int(time.time()))

        return f"{base_key}_v{cache_version}_{params_hash}"

    def list(self, request, *args, **kwargs):
        cache_key = self.get_list_cache_key(request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Cache list for 24 hours
        cache.set(cache_key, data, 86400)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        product_id = kwargs.get('pk')
        cache_key = f"product_detail_{product_id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, 86400)  # Cache for 24 hours
        return response

    def get_queryset(self):
        user = self.request.user
        queryset = Product.objects.select_related('seller', 'category', 'seller__user')
        if not user or not user.is_authenticated:
            return queryset.filter(seller__status="approved")
            
        if user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
            return queryset.all()
            
        if hasattr(user, 'role') and user.role == 'seller':
            return queryset.filter(seller__user=user)
            
        return queryset.filter(seller__status="approved")

    def perform_create(self, serializer):
        user = self.request.user
        seller_profile = getattr(user, 'seller_profile', None)
        if seller_profile:
            if seller_profile.plan == 'starter':
                product_count = Product.objects.filter(seller=seller_profile).count()
                if product_count >= 15:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError(
                        {"detail": "Product listing limit reached. You can list up to 15 products on the Starter plan. Please upgrade your plan in settings."}
                    )
        super().perform_create(serializer)
        from .signals import invalidate_product_cache
        invalidate_product_cache(sender=Product, instance=serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        from .signals import invalidate_product_cache
        invalidate_product_cache(sender=Product, instance=serializer.instance)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        from .signals import invalidate_product_cache
        invalidate_product_cache(sender=Product, instance=instance)


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.id)
        cart_key = f"cart_{user_id}"
        cart_items = cache.get(cart_key, {})
        
        # If action=count is passed:
        action = request.query_params.get("action")
        if action == "count":
            total_items = sum(cart_items.values())
            return Response({"cart_count": total_items})
            
        result = []
        for product_id, quantity in cart_items.items():
            try:
                product = Product.objects.get(id=product_id)
                image_url = None
                if product.image:
                    if isinstance(product.image.name, str) and product.image.name.startswith(('http://', 'https://')):
                        image_url = product.image.name
                    elif product.image.url.startswith(('http://', 'https://')):
                        image_url = product.image.url
                    else:
                        image_url = request.build_absolute_uri(product.image.url)

                result.append({
                    "product_id": product_id,
                    "name": product.name,
                    "price": str(product.price),
                    "image": image_url,
                    "sku": product.sku,
                    "quantity": quantity,
                    "seller_shop": product.seller.shop_name if product.seller else "Platform Store",
                    "seller_id": str(product.seller.id) if product.seller else None
                })
            except Product.DoesNotExist:
                continue
        return Response(result)

    def post(self, request):
        user_id = str(request.user.id)
        cart_key = f"cart_{user_id}"
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get existing cart
        cart_items = cache.get(cart_key, {})
        # Increment quantity
        cart_items[product_id] = cart_items.get(product_id, 0) + quantity
        cache.set(cart_key, cart_items, 86400 * 30) # Save cart for 30 days
        
        # Return total cart items count
        total_items = sum(cart_items.values())
        return Response({
            "message": "Product added to cart",
            "cart_count": total_items
        })

    def delete(self, request):
        user_id = str(request.user.id)
        cart_key = f"cart_{user_id}"
        product_id = request.data.get("product_id")

        if not product_id:
            cache.set(cart_key, {}, 86400 * 30)
            return Response({
                "message": "Cart cleared successfully",
                "cart_count": 0
            })

        cart_items = cache.get(cart_key, {})
        if product_id in cart_items:
            del cart_items[product_id]
            cache.set(cart_key, cart_items, 86400 * 30)

        total_items = sum(cart_items.values())
        return Response({
            "message": "Product removed from cart",
            "cart_count": total_items
        })

    def put(self, request):
        user_id = str(request.user.id)
        cart_key = f"cart_{user_id}"
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity")

        if not product_id:
            return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if quantity is None:
            return Response({"error": "quantity is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError()
        except ValueError:
            return Response({"error": "quantity must be a non-negative integer"}, status=status.HTTP_400_BAD_REQUEST)

        # Get existing cart
        cart_items = cache.get(cart_key, {})

        if quantity == 0:
            if product_id in cart_items:
                del cart_items[product_id]
        else:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            cart_items[product_id] = quantity

        cache.set(cart_key, cart_items, 86400 * 30)

        total_items = sum(cart_items.values())
        return Response({
            "message": "Cart updated successfully",
            "cart_count": total_items
        })


class CloudinarySignatureView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        import time
        import cloudinary.utils
        from django.conf import settings

        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME')
        api_key = getattr(settings, 'CLOUDINARY_API_KEY')
        api_secret = getattr(settings, 'CLOUDINARY_API_SECRET')

        timestamp = int(time.time())
        params = {
            'timestamp': timestamp,
            'folder': 'vendor_nest'
        }
        signature = cloudinary.utils.api_sign_request(params, api_secret)
        return Response({
            'signature': signature,
            'timestamp': timestamp,
            'cloud_name': cloud_name,
            'api_key': api_key,
            'folder': 'vendor_nest'
        })

