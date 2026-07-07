from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework import permissions
from django.contrib.auth import get_user_model
import os
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        
        if not uidb64 or not token:
            return Response({"error": "Missing uid or token."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            
        if user is not None and default_token_generator.check_token(user, token):
            user.is_email_verified = True
            user.is_active = True
            user.save()
            return Response({"message": "Email verified successfully. Your account is now active!"}, status=status.HTTP_200_OK)
            
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            send_mail(
                "Test email - VendorNest",
                "This is a test email to verify Django SMTP settings.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response({"message": f"Test email successfully sent to {email}"}, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return Response({"error": f"Failed to send email: {str(e)}", "traceback": tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

