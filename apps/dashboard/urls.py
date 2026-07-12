from django.urls import path
from .views import AdminDashboardStatsView, AdminReportsStatsView, SaaSSettingsView

urlpatterns = [
    path('admin-stats/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('admin-reports/', AdminReportsStatsView.as_view(), name='admin-reports-stats'),
    path('settings/', SaaSSettingsView.as_view(), name='saas-settings'),
]
