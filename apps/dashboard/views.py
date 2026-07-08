from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import calendar

from orders.models import Order
from seller.models import SellerProfile
from seller.views import IsAdmin

User = get_user_model()

class AdminDashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request, *args, **kwargs):
        # 1. Total Network GMV (Sum of non-cancelled and non-pending orders)
        valid_orders = Order.objects.exclude(status__in=['pending', 'cancelled'])
        total_gmv = valid_orders.aggregate(total=Sum('total_amount'))['total'] or 0.0
        
        # 2. Active Platform Customers
        total_customers = User.objects.filter(role='customer', is_active=True).count()
        
        # 3. Registered Seller Shops (Approved status)
        total_sellers = SellerProfile.objects.filter(status='approved').count()
        
        # 4. SaaS Platform Revenue (10% of valid orders GMV)
        total_gmv_float = float(total_gmv)
        platform_revenue = total_gmv_float * 0.10
        
        # 5. Monthly Revenue for the last 6 months
        now = timezone.now()
        months_list = []
        for i in range(5, -1, -1):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            months_list.append((y, m))
            
        monthly_stats = {}
        for y, m in months_list:
            # Aggregate orders for that specific month and year
            month_orders = valid_orders.filter(created_at__year=y, created_at__month=m)
            month_gmv = month_orders.aggregate(total=Sum('total_amount'))['total'] or 0.0
            month_revenue = float(month_gmv) * 0.10
            
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
            "total_gmv": round(total_gmv_float, 2),
            "total_customers": total_customers,
            "total_sellers": total_sellers,
            "platform_revenue": round(platform_revenue, 2),
            "chart_data": chart_data
        })
