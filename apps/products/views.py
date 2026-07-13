from rest_framework.views import APIView
from rest_framework import status
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.cache import cache
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Product, ProductVersion, ProductLicenseKey
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
        
        # Admin / Superuser see all products
        if user and user.is_authenticated and (user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')):
            return queryset.all()
            
        # Sellers see only their own products
        if user and user.is_authenticated and hasattr(user, 'role') and user.role == 'seller':
            return queryset.filter(seller__user=user)
            
        # Visitors / Customers see approved seller's approved and published products
        now = timezone.now()
        return queryset.filter(
            seller__status="approved",
            approval_status="approved"
        ).filter(
            models.Q(publish_at__isnull=True) | models.Q(publish_at__lte=now)
        )

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

    # 1. Product Approval Workflow: Approve
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        user = request.user
        is_admin = user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')
        if not is_admin:
            return Response({"error": "Only administrators can approve products."}, status=status.HTTP_403_FORBIDDEN)
            
        product = self.get_object()
        product.approval_status = 'approved'
        product._changed_by = user
        product.save()
        
        from .signals import invalidate_product_cache
        invalidate_product_cache(sender=Product, instance=product)
        return Response({"message": "Product approved successfully.", "status": "approved"})

    # 2. Product Approval Workflow: Reject
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        user = request.user
        is_admin = user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')
        if not is_admin:
            return Response({"error": "Only administrators can reject products."}, status=status.HTTP_403_FORBIDDEN)
            
        product = self.get_object()
        product.approval_status = 'rejected'
        product._changed_by = user
        product.save()
        
        from .signals import invalidate_product_cache
        invalidate_product_cache(sender=Product, instance=product)
        return Response({"message": "Product rejected successfully.", "status": "rejected"})

    # 3. Product Version History Log Viewer
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def versions(self, request, pk=None):
        product = self.get_object()
        user = request.user
        is_admin = user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')
        is_owner = hasattr(user, 'role') and user.role == 'seller' and product.seller.user == user
        
        if not is_admin and not is_owner:
            return Response({"error": "Unauthorized to view version logs for this product."}, status=status.HTTP_403_FORBIDDEN)
            
        from .serializers import ProductVersionSerializer
        versions = product.versions.all().order_by('-version_number')
        serializer = ProductVersionSerializer(versions, many=True)
        return Response(serializer.data)

    # 4. Bulk CSV Export Action
    @action(detail=False, methods=['get'], url_path='bulk-export', permission_classes=[permissions.IsAuthenticated])
    def bulk_export(self, request):
        import csv
        from django.http import HttpResponse
        
        products = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vendornest_products_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'id', 'name', 'category', 'sku', 'price', 'compare_at_price', 
            'stock', 'low_stock_threshold', 'description', 'is_digital', 
            'digital_file_url', 'license_keys', 'name_bn', 'description_bn'
        ])
        
        for p in products:
            writer.writerow([
                str(p.id),
                p.name,
                p.category.name if p.category else '',
                p.sku or '',
                float(p.price),
                float(p.compare_at_price) if p.compare_at_price else '',
                p.stock,
                p.low_stock_threshold,
                p.description or '',
                p.is_digital,
                p.digital_file_url or '',
                p.license_keys or '',
                p.name_bn or '',
                p.description_bn or ''
            ])
            
        return response

    # 5. Bulk CSV Import Action
    @action(detail=False, methods=['post'], url_path='bulk-import', permission_classes=[permissions.IsAuthenticated])
    def bulk_import(self, request):
        import csv
        import io
        from categories.models import Category
        from seller.models import SellerProfile
        
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({"error": "No CSV file provided under 'file' key."}, status=status.HTTP_400_BAD_REQUEST)
            
        user = request.user
        try:
            seller_profile = user.seller_profile
        except SellerProfile.DoesNotExist:
            seller_profile = SellerProfile.objects.filter(user=user).first()
            if not seller_profile:
                subdomain = "platform-direct"
                if SellerProfile.objects.filter(subdomain=subdomain).exists():
                    subdomain = f"platform-direct-{user.id}"
                seller_profile = SellerProfile.objects.create(
                    user=user,
                    shop_name="Platform Direct (Admin)",
                    subdomain=subdomain,
                    status="approved"
                )
            
        file_data = csv_file.read().decode('utf-8')
        io_string = io.StringIO(file_data)
        reader = csv.DictReader(io_string)
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        for idx, row in enumerate(reader):
            name = row.get('name')
            if not name:
                errors.append(f"Row {idx+1}: Missing required field 'name'.")
                skipped_count += 1
                continue
                
            try:
                cat_name = row.get('category')
                category = None
                if cat_name:
                    category, _ = Category.objects.get_or_create(name=cat_name.strip())
                    
                price = float(row.get('price', 0))
                compare_at_price = row.get('compare_at_price')
                compare_at_price = float(compare_at_price) if compare_at_price else None
                
                stock = int(row.get('stock', 0))
                low_stock_threshold = int(row.get('low_stock_threshold', 10))
                is_digital = row.get('is_digital', 'false').lower() in ['true', '1', 'yes']
                
                product = Product.objects.create(
                    seller=seller_profile,
                    category=category,
                    name=name.strip(),
                    sku=row.get('sku', '').strip() or None,
                    price=price,
                    compare_at_price=compare_at_price,
                    stock=stock,
                    low_stock_threshold=low_stock_threshold,
                    description=row.get('description', ''),
                    is_digital=is_digital,
                    digital_file_url=row.get('digital_file_url', ''),
                    license_keys=row.get('license_keys', ''),
                    name_bn=row.get('name_bn', ''),
                    description_bn=row.get('description_bn', ''),
                    approval_status='approved' if (user.is_staff or user.is_superuser) else 'pending'
                )
                
                if is_digital and product.license_keys:
                    keys = [k.strip() for k in product.license_keys.split('\n') if k.strip()]
                    for key in keys:
                        ProductLicenseKey.objects.create(product=product, key=key)
                        
                created_count += 1
            except Exception as e:
                errors.append(f"Row {idx+1}: {str(e)}")
                skipped_count += 1
                
        # Trigger cache invalidation via version increment
        from django.db.models.signals import post_save
        post_save.send(sender=Product, instance=Product(), created=True)
        
        return Response({
            "message": "Bulk import completed.",
            "created": created_count,
            "skipped": skipped_count,
            "errors": errors
        }, status=status.HTTP_200_OK)


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.id)
        cart_key = f"cart_{user_id}"
        cart_items = cache.get(cart_key, {})
        
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

        cart_items = cache.get(cart_key, {})
        cart_items[product_id] = cart_items.get(product_id, 0) + quantity
        cache.set(cart_key, cart_items, 86400 * 30)
        
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
