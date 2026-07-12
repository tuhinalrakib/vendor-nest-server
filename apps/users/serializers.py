from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models.user import UserProfile
from seller.serializers import SellerProfileSerializer

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "profile_picture",
            "bio",
            "address",
            "city",
            "state",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    seller_profile = SellerProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "first_name",
            "last_name",
            "phone_number",
            "gender",
            "date_of_birth",
            "role",
            "is_email_verified",
            "is_staff",
            "is_active",
            "date_joined",
            "profile",
            "seller_profile",
        ]
        read_only_fields = [
            "id",
            "is_email_verified",
            "is_staff",
            "is_active",
            "date_joined",
        ]

class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            "full_name",
            "first_name",
            "last_name",
            "phone_number",
            "gender",
            "date_of_birth",
            "profile",
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile fields
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            
        return instance

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default="customer")
    
    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
            "full_name",
            "phone_number",
            "role",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        email = validated_data.pop("email")
        
        # Create user with is_active=False until email is verified
        user = User.objects.create_user(
            email=email,
            password=password,
            is_active=False,
            **validated_data
        )
        return user

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role", "is_active"]

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_val = attrs.get(self.username_field)
        password_val = attrs.get("password")
        
        try:
            user = User.objects.get(**{f"{self.username_field}__iexact": username_val})
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "No active account found with the given credentials."}
            )
            
        if not user.check_password(password_val):
            raise serializers.ValidationError(
                {"detail": "The password you entered is incorrect. Please try again."}
            )
            
        if not user.is_active and not user.is_email_verified:
            raise serializers.ValidationError(
                {"detail": "email_not_verified", "message": "Your email is not verified. Please verify your email first."}
            )
            
        data = super().validate(attrs)
        
        # Admin 2FA/OTP login workflow
        if user.role == "admin":
            import uuid
            import random
            from django.core.cache import cache
            from django.core.mail import send_mail
            from django.conf import settings
            import threading
            
            temp_token = uuid.uuid4().hex
            otp = f"{random.randint(100000, 999999)}"
            
            # Store credentials and tokens in cache for 5 minutes (300 seconds)
            cache.set(f"admin_otp_{temp_token}", {
                "user_id": user.id,
                "otp": otp,
                "access": data["access"],
                "refresh": data["refresh"]
            }, timeout=300)
            
            # Send verification email asynchronously
            subject = "Admin Login Verification - OTP Code"
            message = f"Hello {user.get_full_name() or user.username},\n\nA login attempt was made to your admin account on VendorNest.\n\nYour 2FA verification OTP is: {otp}\nThis code is valid for 5 minutes.\n\nIf you did not request this, please secure your account credentials immediately.\n\nBest regards,\nThe VendorNest Team"
            
            def send_otp_email():
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vendornest.com',
                        [user.email],
                        fail_silently=False
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send admin login OTP email to {user.email}: {e}")

            threading.Thread(target=send_otp_email, daemon=True).start()
            
            return {
                "otp_required": True,
                "temp_token": temp_token,
                "email": user.email
            }
            
        return data



