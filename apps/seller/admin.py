from django.contrib import admin
from .models import SellerProfile

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "shop_name", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["user__email", "shop_name"]
    actions = ["approve_sellers", "reject_sellers"]

    def approve_sellers(self, request, queryset):
        queryset.update(status="approved")
        self.message_user(request, "Selected sellers have been approved.")
    approve_sellers.short_description = "Approve selected sellers"

    def reject_sellers(self, request, queryset):
        queryset.update(status="rejected")
        self.message_user(request, "Selected sellers have been rejected.")
    reject_sellers.short_description = "Reject selected sellers"

