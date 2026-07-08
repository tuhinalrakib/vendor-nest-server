from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.core.cache import cache
from .models import Coupon, UserCoupon
from .serializers import CouponSerializer
from seller.models import SellerProfile
from products.models import Product
from decimal import Decimal

class IsAdminOrSellerOrReadOnly(permissions.BasePermission):
    """
    Admin can do anything.
    Approved sellers can manage their own coupons.
    Anyone can list/retrieve active coupons (read-only) for storefront clipping.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user.is_staff or request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return True
        # Sellers can only edit/delete their own coupons
        if hasattr(request.user, 'role') and request.user.role == 'seller':
            return obj.seller and obj.seller.user == request.user
        return False

class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAdminOrSellerOrReadOnly]

    def get_list_cache_key(self, request):
        import hashlib
        import json
        import time

        user = request.user
        if not user or not user.is_authenticated:
            base_key = 'coupons_list_public'
        elif user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
            base_key = 'coupons_list_admin'
        elif hasattr(user, 'role') and user.role == 'seller':
            base_key = f'coupons_list_seller_{user.id}'
        else:
            base_key = f'coupons_list_customer_{user.id}'

        # Hash query parameters to prevent key collisions
        query_params = dict(request.query_params.items())
        params_str = json.dumps(query_params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode('utf-8')).hexdigest()

        # Retrieve/initialize cache version for coupons using timestamp
        cache_version = cache.get_or_set("coupons_cache_version", int(time.time()))

        return f"{base_key}_v{cache_version}_{params_hash}"

    def list(self, request, *args, **kwargs):
        cache_key = self.get_list_cache_key(request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Cache for 24 hours
        cache.set(cache_key, data, 86400)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        coupon_id = kwargs.get('pk')
        cache_key = f"coupon_detail_{coupon_id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, 86400)  # Cache for 24 hours
        return response

    def get_queryset(self):
        user = self.request.user
        # Storefront view / unauthenticated users see only active, unexpired coupons
        if not user or not user.is_authenticated:
            return Coupon.objects.filter(is_active=True, expiry_date__gte=timezone.now().date())

        # Admin sees all coupons
        if user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
            # Check query param to filter by seller for convenience
            seller_id = self.request.query_params.get('seller_id')
            if seller_id:
                return Coupon.objects.filter(seller_id=seller_id)
            return Coupon.objects.all()

        # Sellers see their own coupons
        if hasattr(user, 'role') and user.role == 'seller':
            try:
                seller_profile = user.seller_profile
                return Coupon.objects.filter(seller=seller_profile)
            except SellerProfile.DoesNotExist:
                return Coupon.objects.none()

        # Customers see active coupons
        return Coupon.objects.filter(is_active=True, expiry_date__gte=timezone.now().date())

    def perform_create(self, serializer):
        super().perform_create(serializer)
        from .signals import clear_coupons_cache
        clear_coupons_cache()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        from .signals import clear_coupons_cache
        clear_coupons_cache(serializer.instance.id)

    def perform_destroy(self, instance):
        instance_id = instance.id
        super().perform_destroy(instance)
        from .signals import clear_coupons_cache
        clear_coupons_cache(instance_id)


class CouponValidationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        codes = request.data.get("codes", [])
        code = request.data.get("code")
        cart_items = request.data.get("cart_items", [])

        if code and not codes:
            codes = [code]

        if not codes:
            return Response({"error": "No coupon codes provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Normalize coupon codes
        codes = [c.strip().upper() for c in codes if isinstance(c, str)]

        # Group cart items by seller_id and calculate subtotal
        seller_subtotals = {}
        total_subtotal = Decimal("0.00")
        
        for item in cart_items:
            price = Decimal(str(item.get("price", "0.00")))
            quantity = int(item.get("quantity", 1))
            seller_id = item.get("seller_id")
            
            # If seller_id is missing on the client, try to resolve it from database
            if not seller_id:
                product_id = item.get("product_id")
                if product_id:
                    try:
                        product = Product.objects.get(id=product_id)
                        if product.seller:
                            seller_id = str(product.seller.id)
                    except Product.DoesNotExist:
                        pass
            
            item_subtotal = price * quantity
            total_subtotal += item_subtotal
            
            if seller_id:
                seller_subtotals[seller_id] = seller_subtotals.get(seller_id, Decimal("0.00")) + item_subtotal

        applied_coupons = []
        invalid_coupons = []
        total_discount = Decimal("0.00")
        current_date = timezone.now().date()

        for c_code in codes:
            try:
                coupon = Coupon.objects.get(code=c_code)
            except Coupon.DoesNotExist:
                invalid_coupons.append({
                    "code": c_code,
                    "reason": "Coupon code is invalid."
                })
                continue

            # Check if user has already used this coupon
            if request.user and request.user.is_authenticated:
                if UserCoupon.objects.filter(user=request.user, coupon=coupon, is_used=True).exists():
                    invalid_coupons.append({
                        "code": c_code,
                        "reason": "You have already used this coupon."
                    })
                    continue

            # Check if active
            if not coupon.is_active:
                invalid_coupons.append({
                    "code": c_code,
                    "reason": "Coupon is inactive."
                })
                continue

            # Check if expired
            if coupon.expiry_date < current_date:
                invalid_coupons.append({
                    "code": c_code,
                    "reason": "Coupon has expired."
                })
                # Automatically disable expired coupon to keep DB clean
                coupon.is_active = False
                coupon.save()
                continue

            # Check matching items subtotal depending on coupon type
            discount_amount = Decimal("0.00")
            if coupon.seller:
                # Seller specific coupon
                seller_id = str(coupon.seller.id)
                matching_subtotal = seller_subtotals.get(seller_id, Decimal("0.00"))
                
                if matching_subtotal == 0:
                    invalid_coupons.append({
                        "code": c_code,
                        "reason": f"This coupon is only valid for products from {coupon.seller.shop_name}."
                    })
                    continue

                if matching_subtotal < coupon.min_purchase:
                    invalid_coupons.append({
                        "code": c_code,
                        "reason": f"Minimum purchase of ${coupon.min_purchase} from {coupon.seller.shop_name} required."
                    })
                    continue

                # Calculate discount
                if coupon.discount_type == "percentage":
                    discount_amount = matching_subtotal * (coupon.discount_value / Decimal("100.00"))
                else: # fixed
                    discount_amount = min(coupon.discount_value, matching_subtotal)

                # Track changes to prevent double-discounting seller subtotal beyond 0
                discount_amount = min(discount_amount, matching_subtotal)
                # Deduct from seller subtotal so subsequent seller coupons (if any) apply on remaining
                seller_subtotals[seller_id] -= discount_amount
                total_subtotal -= discount_amount

            else:
                # Admin / Global coupon
                if total_subtotal < coupon.min_purchase:
                    invalid_coupons.append({
                        "code": c_code,
                        "reason": f"Minimum overall purchase of ${coupon.min_purchase} required."
                    })
                    continue

                # Calculate discount based on total subtotal remaining
                if coupon.discount_type == "percentage":
                    discount_amount = total_subtotal * (coupon.discount_value / Decimal("100.00"))
                else: # fixed
                    discount_amount = min(coupon.discount_value, total_subtotal)

                # Prevent discounting beyond total
                discount_amount = min(discount_amount, total_subtotal)
                # Deduct from total subtotal
                total_subtotal -= discount_amount

            total_discount += discount_amount
            applied_coupons.append({
                "id": str(coupon.id),
                "code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": str(coupon.discount_value),
                "discount_amount": str(discount_amount.quantize(Decimal("0.01"))),
                "seller_id": str(coupon.seller.id) if coupon.seller else None,
                "seller_shop": coupon.seller.shop_name if coupon.seller else "Platform Sitewide"
            })

        return Response({
            "valid": len(applied_coupons) > 0,
            "applied_coupons": applied_coupons,
            "invalid_coupons": invalid_coupons,
            "total_discount": str(total_discount.quantize(Decimal("0.01"))),
            "final_subtotal": str(max(Decimal("0.00"), total_subtotal).quantize(Decimal("0.01")))
        })


class SaveCouponView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        coupon_id = request.data.get("coupon_id")
        coupon_code = request.data.get("code")
        
        if not coupon_id and not coupon_code:
            return Response({"error": "Coupon ID or Code is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            if coupon_id:
                coupon = Coupon.objects.get(id=coupon_id)
            else:
                coupon = Coupon.objects.get(code=coupon_code.strip().upper())
        except (Coupon.DoesNotExist, ValueError):
            return Response({"error": "Coupon not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if not coupon.is_active or coupon.expiry_date < timezone.now().date():
            return Response({"error": "Coupon is expired or inactive."}, status=status.HTTP_400_BAD_REQUEST)
            
        user_coupon, created = UserCoupon.objects.get_or_create(
            user=request.user,
            coupon=coupon,
            defaults={"is_used": False}
        )
        
        if not created:
            if user_coupon.is_used:
                return Response({"error": "You have already used this coupon."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Coupon is already saved."}, status=status.HTTP_200_OK)
            
        return Response({"message": "Coupon saved successfully.", "is_clipped": True}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        coupon_id = request.data.get("coupon_id")
        coupon_code = request.data.get("code")
        
        if not coupon_id and not coupon_code:
            return Response({"error": "Coupon ID or Code is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            if coupon_id:
                user_coupon = UserCoupon.objects.get(user=request.user, coupon_id=coupon_id)
            else:
                user_coupon = UserCoupon.objects.get(user=request.user, coupon__code=coupon_code.strip().upper())
            
            if user_coupon.is_used:
                return Response({"error": "Cannot remove a used coupon."}, status=status.HTTP_400_BAD_REQUEST)
                
            user_coupon.delete()
            return Response({"message": "Coupon unsaved successfully.", "is_clipped": False}, status=status.HTTP_200_OK)
        except UserCoupon.DoesNotExist:
            return Response({"error": "Saved coupon not found."}, status=status.HTTP_404_NOT_FOUND)


class SavedCouponsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_coupons = UserCoupon.objects.filter(
            user=request.user,
            is_used=False,
            coupon__is_active=True,
            coupon__expiry_date__gte=timezone.now().date()
        ).select_related('coupon')
        
        coupons = [uc.coupon for uc in user_coupons]
        serializer = CouponSerializer(coupons, many=True, context={'request': request})
        return Response(serializer.data)


class ApplicableCouponsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart_items = request.data.get("cart_items", [])
        if not cart_items:
            return Response([], status=status.HTTP_200_OK)

        # Calculate subtotals
        seller_subtotals = {}
        total_subtotal = Decimal("0.00")
        for item in cart_items:
            price = Decimal(str(item.get("price", "0.00")))
            quantity = int(item.get("quantity", 1))
            seller_id = item.get("seller_id")
            
            if not seller_id:
                product_id = item.get("product_id")
                if product_id:
                    try:
                        product = Product.objects.get(id=product_id)
                        if product.seller:
                            seller_id = str(product.seller.id)
                    except Product.DoesNotExist:
                        pass
            
            item_subtotal = price * quantity
            total_subtotal += item_subtotal
            if seller_id:
                seller_subtotals[seller_id] = seller_subtotals.get(seller_id, Decimal("0.00")) + item_subtotal

        # Fetch active, unexpired coupons that the user has NOT already used
        current_date = timezone.now().date()
        used_coupon_ids = UserCoupon.objects.filter(user=request.user, is_used=True).values_list('coupon_id', flat=True)
        active_coupons = Coupon.objects.filter(is_active=True, expiry_date__gte=current_date).exclude(id__in=used_coupon_ids)
        
        # Filter coupons that are eligible based on the cart subtotal / seller subtotal
        eligible_coupons = []
        for coupon in active_coupons:
            if coupon.seller:
                seller_id = str(coupon.seller.id)
                if seller_id in seller_subtotals:
                    if seller_subtotals[seller_id] >= coupon.min_purchase:
                        eligible_coupons.append(coupon)
            else:
                if total_subtotal >= coupon.min_purchase:
                    eligible_coupons.append(coupon)

        serializer = CouponSerializer(eligible_coupons, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

