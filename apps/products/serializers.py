from rest_framework import serializers
from django.utils.text import slugify
from .models import Product, Review
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

class ProductSerializer(serializers.ModelSerializer):
    seller_shop = serializers.SerializerMethodField()
    color = serializers.CharField(required=False, allow_blank=True, default="")
    sizes = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Product
        fields = [
            'id', 'seller', 'seller_shop', 'category', 'name', 'slug', 
            'sku', 'price', 'compare_at_price', 'stock', 'description', 
            'seo_title', 'seo_description', 'tags', 'image', 'color', 'sizes'
        ]
        read_only_fields = ['id', 'seller']

    def get_seller_shop(self, obj):
        return obj.seller.shop_name if obj.seller else "Platform Direct (Admin)"

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
            # For admin, get or create default admin seller profile
            seller_profile, _ = SellerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "shop_name": "Platform Direct (Admin)",
                    "subdomain": "platform-direct",
                    "status": "approved"
                }
            )
        else:
            # For regular seller, get their own seller profile
            try:
                seller_profile = user.seller_profile
            except SellerProfile.DoesNotExist:
                raise serializers.ValidationError({"detail": "User does not have a seller profile."})

        validated_data['seller'] = seller_profile
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Pop extra fields
        color = validated_data.pop('color', None)
        sizes = validated_data.pop('sizes', None)

        if 'name' in validated_data and not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])

        # Auto-generate SKU on update if requested (sku is set to empty) or if the product has no SKU
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

        return super().update(instance, validated_data)


