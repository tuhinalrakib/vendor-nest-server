from rest_framework import serializers
from django.utils.text import slugify
from .models import Product, Review, ProductVersion, ProductLicenseKey
from seller.models import SellerProfile

def get_category_short_form(category_name):
    if not category_name:
        return "PROD"
    words = [w for w in category_name.split() if w.strip()]
    short_form = ""
    for word in words:
        clean_word = "".join(filter(str.isalpha, word))
        if clean_word:
            short_form += clean_word[0].upper()
    return short_form if short_form else "PROD"

def parse_tags_for_extra_fields(tags_str):
    if not tags_str:
        return "", ""
    colors = ""
    sizes = ""
    parts = [p.strip() for p in tags_str.split(",") if p.strip()]
    for part in parts:
        if part.startswith("color:"):
            val = part.replace("color:", "", 1)
            colors = val.replace("|", ", ")
        elif part.startswith("sizes:"):
            val = part.replace("sizes:", "", 1)
            sizes = val.replace("|", ", ")
    return colors, sizes

class HybridImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith(('http://', 'https://')):
            return data
        return super().to_internal_value(data)

    def to_representation(self, value):
        if not value:
            return None
        if isinstance(value, str) and value.startswith(('http://', 'https://')):
            return value
        if hasattr(value, 'name') and isinstance(value.name, str) and value.name.startswith(('http://', 'https://')):
            return value.name
        return super().to_representation(value)

class ProductSerializer(serializers.ModelSerializer):
    image = HybridImageField(required=False, allow_null=True)
    seller_shop = serializers.SerializerMethodField()
    color = serializers.CharField(required=False, allow_blank=True, default="")
    sizes = serializers.CharField(required=False, allow_blank=True, default="")
    
    # Read-only generated URLs
    qr_code_url = serializers.SerializerMethodField()
    barcode_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'seller', 'seller_shop', 'category', 'name', 'slug', 
            'sku', 'price', 'compare_at_price', 'stock', 'low_stock_threshold', 'description', 
            'seo_title', 'seo_description', 'tags', 'image', 'color', 'sizes',
            # New fields
            'is_digital', 'digital_file', 'digital_file_url', 'license_keys',
            'approval_status', 'publish_at', 'name_bn', 'description_bn',
            # Generated fields
            'qr_code_url', 'barcode_url'
        ]
        read_only_fields = ['id', 'seller', 'approval_status']

    def get_seller_shop(self, obj):
        return obj.seller.shop_name if obj.seller else "Platform Direct (Admin)"

    def get_qr_code_url(self, obj):
        request = self.context.get('request')
        host = "localhost:3000"
        if request:
            # Try to build clean storefront link
            host_header = request.META.get('HTTP_HOST', 'localhost:8000')
            if '8000' in host_header:
                host = host_header.replace('8000', '3000')
            else:
                host = host_header
        
        # Product details page/modal direct link
        product_url = f"http://{host}/products"
        import urllib.parse
        encoded_url = urllib.parse.quote(product_url)
        return f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encoded_url}"

    def get_barcode_url(self, obj):
        sku = obj.sku or str(obj.id)[:8]
        import urllib.parse
        encoded_sku = urllib.parse.quote(sku)
        return f"https://bwipjs-api.metafloor.com/?bcid=code128&text={encoded_sku}&scale=2&rotate=N&includeText=true"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        colors, sizes = parse_tags_for_extra_fields(instance.tags)
        data['color'] = colors
        data['sizes'] = sizes
        # Clean custom tags displayed to the user
        clean_tags = []
        if instance.tags:
            for tag in instance.tags.split(","):
                tag = tag.strip()
                if not tag.startswith("color:") and not tag.startswith("sizes:"):
                    clean_tags.append(tag)
        data['tags'] = ", ".join(clean_tags)
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        
        # Pop extra fields
        color = validated_data.pop('color', '')
        sizes = validated_data.pop('sizes', '')
        
        # Auto-generate slug if not provided
        if not validated_data.get('slug') and validated_data.get('name'):
            validated_data['slug'] = slugify(validated_data['name'])
            
        # Auto-generate SKU if not provided or empty
        if not validated_data.get('sku'):
            import random
            import string
            price = validated_data.get('price', 0)
            category = validated_data.get('category')
            category_name = category.name if category else "PROD"
            category_code = get_category_short_form(category_name)
            base_sku = f"{category_code}-{int(float(price))}"
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
            sku = f"{base_sku}-{suffix}"
            while Product.objects.filter(sku=sku).exists():
                suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
                sku = f"{base_sku}-{suffix}"
            validated_data['sku'] = sku

        # Merge color and sizes into tags
        tags_list = []
        existing_tags = validated_data.get('tags', '')
        if existing_tags:
            tags_list.append(existing_tags)
        
        if color:
            clean_color = "|".join([c.strip() for c in color.split(",") if c.strip()])
            if clean_color:
                tags_list.append(f"color:{clean_color}")
        if sizes:
            clean_sizes = "|".join([s.strip() for s in sizes.split(",") if s.strip()])
            if clean_sizes:
                tags_list.append(f"sizes:{clean_sizes}")
                
        if tags_list:
            validated_data['tags'] = ", ".join(tags_list)

        # Determine seller profile dynamically based on request user
        if user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
            seller_profile, _ = SellerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "shop_name": "Platform Direct (Admin)",
                    "subdomain": "platform-direct",
                    "status": "approved"
                }
            )
            validated_data['approval_status'] = 'approved'
        else:
            try:
                seller_profile = user.seller_profile
            except SellerProfile.DoesNotExist:
                raise serializers.ValidationError({"detail": "User does not have a seller profile."})
            # Regular sellers go to pending approval
            validated_data['approval_status'] = 'pending'

        validated_data['seller'] = seller_profile
        
        instance = super().create(validated_data)
        instance._changed_by = user
        
        # Populate licenses table from pre-generated keys if digital product
        if instance.is_digital and instance.license_keys:
            keys = [k.strip() for k in instance.license_keys.split('\n') if k.strip()]
            for key in keys:
                ProductLicenseKey.objects.create(product=instance, key=key)

        return instance

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user if request else None

        # Pop extra fields
        color = validated_data.pop('color', None)
        sizes = validated_data.pop('sizes', None)

        if 'name' in validated_data and not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])

        # Auto-generate SKU on update if requested
        if ('sku' in validated_data and not validated_data.get('sku')) or not instance.sku:
            import random
            import string
            price = validated_data.get('price', instance.price)
            category = validated_data.get('category', instance.category)
            category_name = category.name if category else "PROD"
            category_code = get_category_short_form(category_name)
            base_sku = f"{category_code}-{int(float(price))}"
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
            sku = f"{base_sku}-{suffix}"
            while Product.objects.filter(sku=sku).exclude(id=instance.id).exists():
                suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
                sku = f"{base_sku}-{suffix}"
            validated_data['sku'] = sku

        # Merge color and sizes into tags on update
        if color is not None or sizes is not None or 'tags' in validated_data:
            current_color, current_sizes = parse_tags_for_extra_fields(instance.tags)
            current_tags_list = []
            if instance.tags:
                for t in instance.tags.split(","):
                    t = t.strip()
                    if not t.startswith("color:") and not t.startswith("sizes:"):
                        current_tags_list.append(t)

            if 'tags' in validated_data:
                new_tags = validated_data.get('tags', '')
                current_tags_list = [t.strip() for t in new_tags.split(",") if t.strip()]

            final_color = color if color is not None else current_color
            final_sizes = sizes if sizes is not None else current_sizes

            final_tags = []
            if current_tags_list:
                final_tags.extend(current_tags_list)
            
            if final_color:
                clean_color = "|".join([c.strip() for c in final_color.split(",") if c.strip()])
                if clean_color:
                    final_tags.append(f"color:{clean_color}")
            if final_sizes:
                clean_sizes = "|".join([s.strip() for s in final_sizes.split(",") if s.strip()])
                if clean_sizes:
                    final_tags.append(f"sizes:{clean_sizes}")

            validated_data['tags'] = ", ".join(final_tags)

        # Set change tracker
        instance._changed_by = user
        updated_instance = super().update(instance, validated_data)

        # Sync/update keys list if keys are modified
        if 'license_keys' in validated_data:
            existing_keys = set(ProductLicenseKey.objects.filter(product=instance).values_list('key', flat=True))
            new_keys = set([k.strip() for k in (validated_data.get('license_keys') or '').split('\n') if k.strip()])
            
            # Create keys that do not exist yet
            keys_to_create = new_keys - existing_keys
            for key in keys_to_create:
                ProductLicenseKey.objects.create(product=instance, key=key)
            
            # Delete unassigned keys that were removed
            keys_to_delete = existing_keys - new_keys
            ProductLicenseKey.objects.filter(product=instance, key__in=keys_to_delete, is_assigned=False).delete()

        return updated_instance


class ProductVersionSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = ProductVersion
        fields = ['id', 'version_number', 'changed_by_name', 'changes', 'created_at']

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S") if obj.created_at else "N/A"
