from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from users.serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "Successfully logged out"}, 
                status=status.HTTP_200_OK
            )
        except TokenError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Something went wrong"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class VerifyAdminOTPView(APIView):
    """
    Endpoint to verify 2FA/OTP code for Admin login and return final JWT tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        temp_token = request.data.get("temp_token")
        otp = request.data.get("otp")

        if not temp_token or not otp:
            return Response(
                {"error": "Temporary token and verification code are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.core.cache import cache
        cached_data = cache.get(f"admin_otp_{temp_token}")

        if not cached_data:
            return Response(
                {"error": "The verification session has expired. Please log in again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if cached_data["otp"] != otp:
            return Response(
                {"error": "The verification code you entered is incorrect. Please try again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # OTP is correct! Fetch the User
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=cached_data["user_id"])
        except User.DoesNotExist:
            return Response(
                {"error": "The admin account was not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Clear the temporary cache session
        cache.delete(f"admin_otp_{temp_token}")

        # Return final JWT tokens
        return Response(
            {
                "access": cached_data["access"],
                "refresh": cached_data["refresh"],
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_superuser": user.is_superuser
                }
            },
            status=status.HTTP_200_OK
        )


class ResendAdminOTPView(APIView):
    """
    Endpoint to generate and send a new 2FA/OTP code for an active admin login session.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        temp_token = request.data.get("temp_token")

        if not temp_token:
            return Response(
                {"error": "Temporary session token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.core.cache import cache
        cached_data = cache.get(f"admin_otp_{temp_token}")

        if not cached_data:
            return Response(
                {"error": "Your login session has expired. Please log in again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        import random
        from django.core.mail import send_mail
        from django.conf import settings
        import threading
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        try:
            user = User.objects.get(id=cached_data["user_id"])
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate a new OTP and update the cached session (resets the 5 minutes expiry)
        new_otp = f"{random.randint(100000, 999999)}"
        cached_data["otp"] = new_otp
        cache.set(f"admin_otp_{temp_token}", cached_data, timeout=300)

        # Send the new OTP email asynchronously
        from users.utils import send_admin_otp_email
        send_admin_otp_email(user, new_otp, is_resend=True)

        return Response(
            {"message": "A new verification code has been successfully sent to your email."},
            status=status.HTTP_200_OK
        )

