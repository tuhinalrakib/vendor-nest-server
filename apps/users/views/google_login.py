import os
import requests
import uuid
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from ..serializers import UserSerializer
from ..models.user import UserProfile

User = get_user_model()

class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("credential")
        role = request.data.get("role", "customer")  # Default is customer

        if not token:
            return Response(
                {"error": "Credential (Google ID Token) is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate role
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if role not in valid_roles:
            role = "customer"

        # Verify Google Token using Google OAuth2 Tokeninfo API
        try:
            google_verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
            response = requests.get(google_verify_url, timeout=10)
            
            if response.status_code != 200:
                return Response(
                    {"error": "Invalid Google credential"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            payload = response.json()
            
            # Verify issuer
            iss = payload.get("iss", "")
            if iss not in ["accounts.google.com", "https://accounts.google.com"]:
                return Response(
                    {"error": "Invalid token issuer"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Verify Audience / Client ID
            aud = payload.get("aud")
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            if client_id and aud != client_id:
                return Response(
                    {"error": "Audience/Client ID mismatch"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            email = payload.get("email")
            if not email:
                return Response(
                    {"error": "Email address not provided by Google"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get or create User
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                full_name = payload.get("name", "")
                first_name = payload.get("given_name", "")
                last_name = payload.get("family_name", "")
                
                # Generate unique username
                username = email.split('@')[0]
                if User.objects.filter(username=username).exists():
                    username = f"{username}_{uuid.uuid4().hex[:8]}"
                    
                user = User.objects.create_user(
                    email=email,
                    username=username,
                    full_name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    is_active=True,  # Activated immediately since Google verified the email
                    is_email_verified=True
                )
                user.set_unusable_password()
                user.save()
                
                # Profile is automatically created by the post_save signal in signals.py
                
            # Generate Simple JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Google authentication failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
