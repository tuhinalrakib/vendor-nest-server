from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import calendar

from orders.models import Order
from seller.models import SellerProfile
from seller.views import IsAdmin
from .saas_config import SaaSSettings

User = get_user_model()

class IsSuperUser(permissions.BasePermission):
    """
    Allows access only to users with superuser status (is_superuser=True).
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)

class SaaSSettingsView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsSuperUser()]

    def get(self, request):
        config = SaaSSettings.load()
        return Response(config)

    def post(self, request):
        config = SaaSSettings.save(request.data)
        return Response(config)

    def put(self, request):
        return self.post(request)


class AdminDashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request, *args, **kwargs):
        # Load Saas Configuration
        config = SaaSSettings.load()

        # 1. Total Network GMV (Sum of non-cancelled and non-pending orders)
        valid_orders = Order.objects.exclude(status__in=['pending', 'cancelled'])
        total_gmv = valid_orders.aggregate(total=Sum('total_amount'))['total'] or 0.0
        
        # 2. Active Platform Customers
        total_customers = User.objects.filter(role='customer', is_active=True).count()
        
        # 3. Registered Seller Shops (Approved status)
        total_sellers = SellerProfile.objects.filter(status='approved').count()
        
        # 4. SaaS Platform Revenue (calculated dynamically based on seller plan rates)
        platform_revenue = 0.0
        for order in valid_orders.prefetch_related('items__product__seller'):
            for item in order.items.all():
                if item.product and item.product.seller:
                    plan = item.product.seller.plan
                    if plan == 'growth':
                        rate = float(config.get('growth_commission_rate', 2.0)) / 100.0
                    elif plan == 'enterprise':
                        rate = float(config.get('enterprise_commission_rate', 0.5)) / 100.0
                    else: # starter
                        rate = float(config.get('starter_commission_rate', 5.0)) / 100.0
                    platform_revenue += float(item.price * item.quantity) * rate
        
        # 5. Monthly Revenue for the last 6 months (centered on latest order if any, else now)
        latest_order = valid_orders.order_by('-created_at').first()
        reference_date = latest_order.created_at if latest_order else timezone.now()
        
        months_list = []
        for i in range(5, -1, -1):
            m = reference_date.month - i
            y = reference_date.year
            while m <= 0:
                m += 12
                y -= 1
            months_list.append((y, m))
            
        monthly_stats = {}
        for y, m in months_list:
            # Aggregate orders for that specific month and year
            month_orders = valid_orders.filter(created_at__year=y, created_at__month=m).prefetch_related('items__product__seller')
            month_revenue = 0.0
            for order in month_orders:
                for item in order.items.all():
                    if item.product and item.product.seller:
                        plan = item.product.seller.plan
                        if plan == 'growth':
                            rate = float(config.get('growth_commission_rate', 2.0)) / 100.0
                        elif plan == 'enterprise':
                            rate = float(config.get('enterprise_commission_rate', 0.5)) / 100.0
                        else: # starter
                            rate = float(config.get('starter_commission_rate', 5.0)) / 100.0
                        month_revenue += float(item.price * item.quantity) * rate
            
            month_label = calendar.month_abbr[m]
            monthly_stats[f"{y}-{m}"] = {
                "label": month_label,
                "value": round(month_revenue, 2)
            }
            
        chart_data = []
        for y, m in months_list:
            key = f"{y}-{m}"
            chart_data.append(monthly_stats[key])
            
        return Response({
            "total_gmv": round(float(total_gmv), 2),
            "total_customers": total_customers,
            "total_sellers": total_sellers,
            "platform_revenue": round(platform_revenue, 2),
            "chart_data": chart_data
        })


class AdminReportsStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request, *args, **kwargs):
        from payments.models import Payout
        config = SaaSSettings.load()
        
        # 1. Commission Fee (calculated dynamically based on seller plan rates)
        valid_orders = Order.objects.exclude(status__in=['pending', 'cancelled'])
        commission_fee = 0.0
        for order in valid_orders.prefetch_related('items__product__seller'):
            for item in order.items.all():
                if item.product and item.product.seller:
                    plan = item.product.seller.plan
                    if plan == 'growth':
                        rate = float(config.get('growth_commission_rate', 2.0)) / 100.0
                    elif plan == 'enterprise':
                        rate = float(config.get('enterprise_commission_rate', 0.5)) / 100.0
                    else: # starter
                        rate = float(config.get('starter_commission_rate', 5.0)) / 100.0
                    commission_fee += float(item.price * item.quantity) * rate
        
        # 2. Onboarding Fees ($50 per approved seller)
        approved_sellers = SellerProfile.objects.filter(status='approved')
        onboarding_fees = approved_sellers.count() * 50.0
        
        # 3. Seller Subscriptions MRR
        growth_count = approved_sellers.filter(plan='growth').count()
        enterprise_count = approved_sellers.filter(plan='enterprise').count()
        seller_subscriptions_mrr = (growth_count * 29.0) + (enterprise_count * 79.0)
        
        # 4. Domain Surcharges ($10 per premium seller)
        domain_surcharges = (growth_count + enterprise_count) * 10.0
        
        # 5. Net Platform Earnings
        net_earnings = commission_fee + onboarding_fees + seller_subscriptions_mrr + domain_surcharges
        
        # 6. Pending Seller Payouts
        pending_payouts_sum = Payout.objects.filter(status__in=['pending', 'processing']).aggregate(total=Sum('amount'))['total'] or 0.0
        pending_payouts_sum = float(pending_payouts_sum)
        
        # 7. Reports Breakdown Chart Data
        reports_breakdown = [
            {"label": "Commission Fee", "value": round(commission_fee, 2)},
            {"label": "Onboarding Fees", "value": round(onboarding_fees, 2)},
            {"label": "Seller Subscription", "value": round(seller_subscriptions_mrr, 2)},
            {"label": "Domain Surcharges", "value": round(domain_surcharges, 2)},
        ]
        
        # 8. Top Seller Payouts Chart Data
        payouts_summary = Payout.objects.filter(status='completed').values('seller__shop_name').annotate(total_paid=Sum('amount')).order_by('-total_paid')[:4]
        seller_payouts = []
        for p in payouts_summary:
            seller_payouts.append({
                "label": p['seller__shop_name'] or "Unnamed Shop",
                "value": float(p['total_paid'])
            })
        
        # Fallback to make the chart look nice even if no completed payouts exist yet
        if not seller_payouts:
            top_sellers = approved_sellers.order_by('-balance')[:4]
            for s in top_sellers:
                seller_payouts.append({
                    "label": s.shop_name or "Unnamed Shop",
                    "value": float(s.balance)
                })
        
        # 9. Payout Schedules Table
        payout_list = Payout.objects.all().order_by('-created_at')[:15]
        payouts_table = []
        for p in payout_list:
            payouts_table.append({
                "id": str(p.id),
                "shop_name": p.seller.shop_name or "Unnamed Shop",
                "payout_account": p.payout_email_or_account,
                "amount": float(p.amount),
                "status": p.status,
                "date": p.created_at.strftime("%Y-%m-%d") if p.created_at else "N/A"
            })
            
        return Response({
            "net_earnings": round(net_earnings, 2),
            "pending_payouts": round(pending_payouts_sum, 2),
            "mrr": round(seller_subscriptions_mrr, 2),
            "reports_breakdown": reports_breakdown,
            "seller_payouts": seller_payouts,
            "payouts_table": payouts_table
        })
