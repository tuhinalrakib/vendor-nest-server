from rest_framework import views, viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from .models import Transaction, Payout, PayoutSettings
from .serializers import TransactionSerializer, PayoutSerializer, PayoutSettingsSerializer
from orders.models import Order
from seller.models import SellerProfile
from .gateways.stripe_client import StripeSandboxClient
from .gateways.shurjopay_client import ShurjopaySandboxClient
from .gateways.wise_client import WiseSandboxClient
from .gateways.payoneer_client import PayoneerSandboxClient
from decimal import Decimal
import logging
import uuid

logger = logging.getLogger(__name__)

class StripeCheckoutSessionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        order = get_object_or_404(Order, id=order_id)
        
        success_url = f"http://127.0.0.1:8000/api/payments/stripe/verify/?session_id={{CHECKOUT_SESSION_ID}}&order_id={order_id}&status=success"
        cancel_url = f"http://127.0.0.1:8000/api/payments/stripe/verify/?status=cancel"
        
        session = StripeSandboxClient.create_checkout_session(
            order_id=order_id,
            amount=str(order.total_amount),
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        Transaction.objects.create(
            order=order,
            amount=order.total_amount,
            payment_method='stripe',
            status='pending',
            transaction_id=session["id"]
        )

        return Response({
            "checkout_url": session["checkout_url"],
            "session_id": session["id"]
        })

class StripeVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        status_param = request.query_params.get("status")
        order_id = request.query_params.get("order_id")

        if not session_id and order_id:
            try:
                tx = Transaction.objects.filter(order_id=order_id, payment_method='stripe').latest('created_at')
                session_id = tx.transaction_id
            except Transaction.DoesNotExist:
                pass

        if not session_id:
            return Response({"error": "Session ID is missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tx = Transaction.objects.get(transaction_id=session_id)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        if status_param == "success":
            res = StripeSandboxClient.verify_payment(session_id)
            if res["status"] == "succeeded":
                tx.status = "completed"
                tx.save()
                
                order = tx.order
                order.status = "paid"
                order.save()
                
                return redirect(f"http://localhost:3000/order-success?type=stripe&order_id={order.id}")
                
        tx.status = "failed"
        tx.save()
        return redirect("http://localhost:3000/checkout?checkout_success=false")


class ShurjopayInitiateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, id=order_id)
        
        # Initiate payment
        init_res = ShurjopaySandboxClient.initiate_payment(
            amount=str(order.total_amount),
            return_url="http://127.0.0.1:8000/api/payments/shurjopay/callback/",
            cancel_url="http://127.0.0.1:8000/api/payments/shurjopay/callback/?status=cancel"
        )

        # Create pending transaction
        Transaction.objects.create(
            order=order,
            amount=order.total_amount,
            payment_method='shurjopay',
            status='pending',
            transaction_id=init_res["sp_tx_id"]
        )

        return Response({
            "checkout_url": init_res["checkout_url"],
            "sp_tx_id": init_res["sp_tx_id"]
        })

class ShurjopayCallbackView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        sp_tx_id = request.query_params.get("sp_tx_id")
        status_param = request.query_params.get("status")

        if not sp_tx_id:
            return Response({"error": "Transaction ID is missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tx = Transaction.objects.get(transaction_id=sp_tx_id)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        if status_param == "success":
            # Verify transaction
            res = ShurjopaySandboxClient.verify_payment(sp_tx_id)
            if res["status"] == "success":
                tx.status = "completed"
                tx.save()
                
                # Mark order paid
                order = tx.order
                order.status = "paid"
                order.save()
                
                # Redirect back to the frontend success landing area
                return redirect(f"http://localhost:3000/order-success?type=shurjopay&order_id={order.id}")
                
        tx.status = "failed"
        tx.save()
        return redirect("http://localhost:3000/checkout?checkout_success=false")


class CODPaymentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, id=order_id)

        # Create Cash on Delivery transaction record
        # Status = 'cod_pending' conceptually — cash will be collected on delivery.
        # We mark transaction as 'pending' (cash not yet received) but order as 'cod_confirmed'.
        Transaction.objects.create(
            order=order,
            amount=order.total_amount,
            payment_method='cod',
            status='pending',  # Cash not yet collected — will be on delivery
            transaction_id=f"cod_{uuid.uuid4().hex[:12]}"
        )

        # Mark order as COD Confirmed — distinct from unpaid "pending" orders
        order.status = "cod_confirmed"
        order.payment_method = "cod"
        order.save()

        return Response({
            "status": "success",
            "message": "Cash on Delivery order confirmed. Pay the delivery agent upon arrival.",
            "order_id": str(order.id),
            "order_status": order.status,
        })


class PayoutSettingsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, "seller_profile"):
            return Response({"error": "Only sellers possess payout configurations."}, status=status.HTTP_403_FORBIDDEN)
        
        settings_obj, _ = PayoutSettings.objects.get_or_create(seller=request.user.seller_profile)
        serializer = PayoutSettingsSerializer(settings_obj)
        return Response(serializer.data)

    def put(self, request):
        if not hasattr(request.user, "seller_profile"):
            return Response({"error": "Only sellers possess payout configurations."}, status=status.HTTP_430_FORBIDDEN)

        settings_obj, _ = PayoutSettings.objects.get_or_create(seller=request.user.seller_profile)
        serializer = PayoutSettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
            return Payout.objects.all()
        if hasattr(user, "seller_profile"):
            return Payout.objects.filter(seller=user.seller_profile)
        return Payout.objects.none()

    def create(self, request):
        user = request.user
        if not hasattr(user, "seller_profile"):
            return Response({"error": "Only sellers can request payouts."}, status=status.HTTP_403_FORBIDDEN)
        
        amount = Decimal(str(request.data.get("amount", "0.00")))
        payout_method = request.data.get("payout_method")
        
        if amount <= 0:
            return Response({"error": "Payout amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)
        if payout_method not in ["payoneer", "wise"]:
            return Response({"error": "Invalid payout method."}, status=status.HTTP_400_BAD_REQUEST)

        # Get payout credentials
        seller = user.seller_profile
        try:
            settings_obj = seller.payout_settings
        except PayoutSettings.DoesNotExist:
            return Response({"error": "Please configure payout settings details first."}, status=status.HTTP_400_BAD_REQUEST)

        payout_dest = ""
        if payout_method == "payoneer":
            payout_dest = settings_obj.payoneer_email
            if not payout_dest:
                return Response({"error": "Payoneer email configuration is missing."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            payout_dest = settings_obj.wise_iban_or_account
            if not payout_dest:
                return Response({"error": "Wise account/IBAN configuration is missing."}, status=status.HTTP_400_BAD_REQUEST)

        # Record payout request
        payout = Payout.objects.create(
            seller=seller,
            amount=amount,
            payout_method=payout_method,
            status='pending',
            payout_email_or_account=payout_dest
        )
        
        serializer = self.get_serializer(payout)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PayoutDisburseView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        payout = get_object_or_404(Payout, id=pk)
        if payout.status != "pending":
            return Response({"error": "Payout has already been processed."}, status=status.HTTP_400_BAD_REQUEST)

        payout.status = "processing"
        payout.save()

        try:
            ref = f"Payout_{payout.id.hex[:8]}"
            if payout.payout_method == "payoneer":
                # Verify and disburse Payoneer
                verify_res = PayoneerSandboxClient.verify_recipient(payout.payout_email_or_account)
                payout_res = PayoneerSandboxClient.initiate_payout(
                    payoneer_id=verify_res["payoneer_id"],
                    amount=str(payout.amount),
                    reference=ref
                )
                payout.reference_id = payout_res["payout_id"]
                payout.status = "completed"
            
            else: # wise
                recipient_res = WiseSandboxClient.create_recipient(
                    name=payout.seller.payout_settings.wise_recipient_name or payout.seller.shop_name or "Seller Merchant",
                    account_details=payout.payout_email_or_account
                )
                quote_res = WiseSandboxClient.create_quote(
                    source_currency="USD",
                    target_currency="USD",
                    amount=str(payout.amount)
                )
                transfer_res = WiseSandboxClient.create_transfer(
                    recipient_id=recipient_res["id"],
                    quote_id=quote_res["id"],
                    reference=ref
                )
                payout.reference_id = transfer_res["id"]
                payout.status = "completed"

            payout.save()
            return Response({
                "status": "success",
                "message": f"Disbursed ${payout.amount} successfully.",
                "reference_id": payout.reference_id
            })

        except Exception as e:
            payout.status = "failed"
            payout.save()
            logger.error(f"Failed to disburse payout: {e}")
            return Response({"error": "Disbursal request failed in sandbox gateways."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
