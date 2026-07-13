import uuid
from django.db import models
from core.models import BaseModel
from django.contrib.auth import get_user_model
from products.models import Product

User = get_user_model()

class Order(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),          # Created, awaiting payment
        ("cod_confirmed", "COD Confirmed"),  # Cash on Delivery — confirmed, pay on delivery
        ("paid", "Paid"),                # Online payment completed
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("stripe", "Stripe"),
        ("sslcommerz", "SSLCommerz"),
        ("cod", "Cash on Delivery"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Shipping Details
    shipping_name = models.CharField(max_length=255, blank=True, null=True)
    shipping_phone = models.CharField(max_length=20, blank=True, null=True)
    shipping_address = models.CharField(max_length=255, blank=True, null=True)
    shipping_city = models.CharField(max_length=100, blank=True, null=True)
    shipping_zip = models.CharField(max_length=20, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    stock_deducted = models.BooleanField(default=False)
    ledger_credited = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    # Tracking Details
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    courier_name = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # We need to save the order first to ensure it has an ID and items can be accessed,
        # but wait, items are added after the order is created. 
        # So at creation, there are no items. 
        # We should check the status, save the order, and then if it's a qualifying status 
        # and stock_deducted is False, we deduct stock.
        super().save(*args, **kwargs)
        
        if self.status in ["paid", "delivered", "cod_confirmed"]:
            stock_updated = False
            
            if not self.stock_deducted:
                items = self.items.all()
                if items.exists():
                    from django.core.mail import send_mail
                    from django.conf import settings
                    for item in items:
                        if item.product:
                            # Handle Digital License Key Assignment
                            if item.product.is_digital:
                                from products.models import ProductLicenseKey
                                available_keys = ProductLicenseKey.objects.filter(product=item.product, is_assigned=False)[:item.quantity]
                                for key_obj in available_keys:
                                    key_obj.is_assigned = True
                                    key_obj.assigned_to_order_item = item
                                    key_obj.save()
                                
                                keys_found = len(available_keys)
                                if keys_found < item.quantity:
                                    import uuid
                                    for _ in range(item.quantity - keys_found):
                                        ProductLicenseKey.objects.create(
                                            product=item.product,
                                            key=f"LIC-{uuid.uuid4().hex[:16].upper()}",
                                            is_assigned=True,
                                            assigned_to_order_item=item
                                        )
                            # Handle Physical Product Stock
                            else:
                                old_stock = item.product.stock
                                new_stock = max(0, old_stock - item.quantity)
                                item.product.stock = new_stock
                                item.product.save()

                                # Trigger email alerts on transitions
                                seller_profile = item.product.seller
                                if seller_profile:
                                    recipient_email = seller_profile.support_email or (seller_profile.user.email if seller_profile.user else None)
                                    if recipient_email:
                                        from users.utils import send_stock_alert_email
                                        if old_stock > 0 and new_stock == 0:
                                            send_stock_alert_email(
                                                recipient_email=recipient_email,
                                                shop_name=seller_profile.shop_name,
                                                product_name=item.product.name,
                                                sku=item.product.sku,
                                                new_stock=new_stock,
                                                is_out_of_stock=True
                                            )
                                        elif old_stock >= item.product.low_stock_threshold and 0 < new_stock < item.product.low_stock_threshold:
                                            send_stock_alert_email(
                                                recipient_email=recipient_email,
                                                shop_name=seller_profile.shop_name,
                                                product_name=item.product.name,
                                                sku=item.product.sku,
                                                new_stock=new_stock,
                                                is_out_of_stock=False
                                            )
                    stock_updated = True

            ledger_updated = False
            if not self.ledger_credited:
                items = self.items.all()
                if items.exists():
                    from decimal import Decimal
                    for item in items:
                        if item.product and item.product.seller:
                            seller_profile = item.product.seller
                            
                            # SAAS Commission based on Merchant Plan
                            from dashboard.saas_config import SaaSSettings
                            config = SaaSSettings.load()
                            plan = seller_profile.plan
                            if plan == "growth":
                                fee_rate = Decimal(str(config.get("growth_commission_rate", 2.0)))
                            elif plan == "enterprise":
                                fee_rate = Decimal(str(config.get("enterprise_commission_rate", 0.5)))
                            else:  # starter
                                fee_rate = Decimal(str(config.get("starter_commission_rate", 5.0)))
                            
                            commission_rate = fee_rate / Decimal("100.0")
                            item_total = item.price * item.quantity
                            platform_fee = item_total * commission_rate
                            seller_amount = item_total - platform_fee
                            
                            seller_profile.balance += seller_amount
                            seller_profile.save()
                    ledger_updated = True
                
            email_updated = False
            if not self.email_sent:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    subject = f"Order Confirmed - VendorNest [Order #{self.id}]"
                    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
                    backend_url = getattr(settings, 'BACKEND_URL', 'http://127.0.0.1:8000')
                    
                    items = self.items.all()
                    
                    # Plain text fallback
                    message = (
                        f"Hello {self.buyer.username},\n\n"
                        f"Your order #{self.id} has been successfully confirmed.\n"
                        f"Total Amount: ${self.total_amount}\n"
                        f"Payment Method: {self.get_payment_method_display() if self.payment_method else self.get_status_display()}\n\n"
                        f"View details: {frontend_url}/orders\n\n"
                        f"Thank you for shopping with VendorNest!\n\n"
                        f"--\n"
                        f"VendorNest Inc.\n"
                        f"123 Tech Avenue, Suite 400\n"
                        f"Dhaka, Bangladesh 1212\n"
                        f"support@vendornest.com"
                    )
                    
                    # Build HTML order items rows and calculate subtotal
                    items_html = ""
                    subtotal = 0.00
                    for item in items:
                        image_url = "https://placehold.co/80x80/f4f4f5/71717a?text=Product"
                        if item.product.image:
                            try:
                                url = item.product.image.url
                                if url.startswith("http"):
                                    image_url = url
                                else:
                                    image_url = f"{backend_url.rstrip('/')}{url}"
                            except ValueError:
                                pass
                        
                        item_price = float(item.price)
                        item_subtotal = item_price * item.quantity
                        subtotal += item_subtotal
                        items_html += f"""
                        <tr>
                            <td style="padding: 12px 8px; border-bottom: 1px solid #e4e4e7; vertical-align: middle; text-align: left;">
                                <table cellpadding="0" cellspacing="0" style="border-collapse: collapse; text-align: left;">
                                    <tr>
                                        <td style="padding-right: 12px; vertical-align: middle;">
                                            <img src="{image_url}" alt="{item.product.name}" width="48" height="48" style="border-radius: 8px; object-fit: cover; border: 1px solid #e4e4e7; display: block;" />
                                        </td>
                                        <td style="vertical-align: middle;">
                                            <div style="font-weight: 700; font-size: 13px; color: #18181b;">{item.product.name}</div>
                                            <div style="font-size: 11px; color: #71717a; margin-top: 2px;">SKU: {item.product.sku or 'N/A'}</div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                            <td style="padding: 12px 8px; border-bottom: 1px solid #e4e4e7; text-align: center; font-size: 13px; color: #27272a; vertical-align: middle;">{item.quantity}</td>
                            <td style="padding: 12px 8px; border-bottom: 1px solid #e4e4e7; text-align: right; font-size: 13px; color: #27272a; vertical-align: middle;">${item_price:.2f}</td>
                            <td style="padding: 12px 8px; border-bottom: 1px solid #e4e4e7; text-align: right; font-weight: 700; font-size: 13px; color: #18181b; vertical-align: middle;">${item_subtotal:.2f}</td>
                        </tr>
                        """
                    
                    cod_banner = ""
                    if self.payment_method == "cod":
                        cod_banner = f"""
                        <div style="background-color: #fffbeb; border: 1px solid #fef3c7; border-radius: 12px; padding: 16px; margin-bottom: 24px; text-align: left;">
                            <table cellpadding="0" cellspacing="0" style="width: 100%; text-align: left;">
                                <tr>
                                    <td style="vertical-align: middle; width: 40px; padding-right: 12px; font-size: 24px;">
                                        💵
                                    </td>
                                    <td style="vertical-align: middle;">
                                        <div style="font-weight: 800; font-size: 14px; color: #92400e;">Cash on Delivery Confirmed</div>
                                        <div style="font-size: 12px; color: #b45309; margin-top: 4px;">
                                            Please pay <strong>${float(self.total_amount):.2f}</strong> in cash to the delivery agent when your order arrives.
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        """
                        
                    shipping_html = f"""
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; font-size: 12px; color: #334155; line-height: 1.6; text-align: left;">
                        <div style="font-weight: 800; font-size: 11px; color: #0f172a; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Shipping Details</div>
                        <div style="font-weight: 700; color: #1e293b;">{self.shipping_name or self.buyer.username}</div>
                        <div>📞 {self.shipping_phone or 'N/A'}</div>
                        <div style="margin-top: 4px;">📍 {self.shipping_address or 'N/A'}, {self.shipping_city or 'N/A'}, Zip {self.shipping_zip or 'N/A'}</div>
                    </div>
                    """
                    
                    html_message = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                    </head>
                    <body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; -webkit-font-smoothing: antialiased;">
                        <table cellpadding="0" cellspacing="0" style="width: 100%; background-color: #f4f4f5; padding: 40px 20px;">
                            <tr>
                                <td align="center">
                                    <table cellpadding="0" cellspacing="0" style="width: 100%; max-width: 600px; background-color: #ffffff; border-radius: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.02); overflow: hidden; border: 1px solid #e4e4e7;">
                                        <!-- Header Banner -->
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 32px; text-align: center;">
                                                <div style="font-size: 11px; font-weight: 800; color: #c7d2fe; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">Order Confirmed</div>
                                                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 900; letter-spacing: -0.5px;">Thank you for your purchase!</h1>
                                                <div style="color: #e0e7ff; font-size: 13px; margin-top: 8px; font-weight: 500;">Order #{self.id}</div>
                                            </td>
                                        </tr>
                                        
                                        <!-- Content -->
                                        <tr>
                                            <td style="padding: 32px;">
                                                <!-- Welcome -->
                                                <div style="font-size: 15px; color: #27272a; margin-bottom: 24px; text-align: left;">
                                                    Hello <strong style="color: #09090b;">{self.buyer.username}</strong>,<br><br>
                                                    We've received your order and are currently processing it. Here's a summary of your items and delivery details:
                                                </div>
                                                
                                                <!-- COD Banner if applicable -->
                                                {cod_banner}
                                                
                                                <!-- Items Table -->
                                                <div style="font-weight: 800; font-size: 11px; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; text-align: left;">Order Summary</div>
                                                <table cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                                                    <thead>
                                                        <tr style="border-bottom: 2px solid #e4e4e7;">
                                                            <th style="padding: 8px; text-align: left; font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase;">Item</th>
                                                            <th style="padding: 8px; text-align: center; font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase; width: 60px;">Qty</th>
                                                            <th style="padding: 8px; text-align: right; font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase; width: 80px;">Price</th>
                                                            <th style="padding: 8px; text-align: right; font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase; width: 90px;">Total</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {items_html}
                                                    </tbody>
                                                </table>
                                                
                                                <!-- Breakdown & Details Grid -->
                                                <table cellpadding="0" cellspacing="0" style="width: 100%; margin-bottom: 32px;">
                                                    <tr>
                                                        <!-- Left: Shipping info -->
                                                        <td style="width: 55%; vertical-align: top; padding-right: 16px; text-align: left;">
                                                            {shipping_html}
                                                        </td>
                                                        
                                                        <!-- Right: Price breakdown -->
                                                        <td style="width: 45%; vertical-align: top; text-align: left;">
                                                            <table cellpadding="0" cellspacing="0" style="width: 100%; font-size: 13px; color: #4b5563;">
                                                                <tr>
                                                                    <td style="padding: 6px 0; text-align: left;">Subtotal</td>
                                                                    <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #1f2937;">${subtotal:.2f}</td>
                                                                </tr>
                                                                <tr>
                                                                    <td style="padding: 6px 0; text-align: left;">Shipping</td>
                                                                    <td style="padding: 6px 0; text-align: right; font-weight: 650; color: #16a34a;">FREE</td>
                                                                </tr>
                                                                <tr style="border-top: 1px dashed #d1d5db;">
                                                                    <td style="padding: 12px 0 0 0; font-size: 14px; font-weight: 800; color: #111827; text-align: left;">Total Amount</td>
                                                                    <td style="padding: 12px 0 0 0; text-align: right; font-size: 16px; font-weight: 900; color: #4f46e5;">${float(self.total_amount):.2f}</td>
                                                                </tr>
                                                                <tr>
                                                                    <td colspan="2" style="padding-top: 12px; text-align: right; font-size: 10px; color: #9ca3af; font-weight: 600;">
                                                                        Payment Method: {self.get_payment_method_display() if self.payment_method else 'Not Specified'}
                                                                    </td>
                                                                </tr>
                                                            </table>
                                                        </td>
                                                    </tr>
                                                </table>
                                                
                                                <!-- CTA Button -->
                                                <div style="text-align: center; margin-bottom: 24px;">
                                                    <a href="{frontend_url}/orders" style="display: inline-block; background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%); color: #ffffff; text-decoration: none; padding: 12px 32px; border-radius: 12px; font-size: 13px; font-weight: 800; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2), 0 2px 4px -1px rgba(79, 70, 229, 0.1); transition: all 0.2s;">
                                                        View Order Dashboard
                                                    </a>
                                                </div>
                                                
                                                <!-- Help footer -->
                                                <div style="border-top: 1px solid #f4f4f5; padding-top: 24px; text-align: center; font-size: 12px; color: #a1a1aa; line-height: 1.5;">
                                                    If you have any questions, simply reply to this email. We're here to help!<br><br>
                                                    <strong>VendorNest Inc.</strong><br>
                                                    123 Tech Avenue, Suite 400<br>
                                                    Dhaka, Bangladesh 1212<br>
                                                    <a href="mailto:support@vendornest.com" style="color: #4f46e5; text-decoration: none;">support@vendornest.com</a>
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </body>
                    </html>
                    """
                    
                    import threading
                    
                    def send_async_emails():
                        try:
                            # 1. Send confirmation email to the buyer
                            send_mail(
                                subject,
                                message,
                                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vendornest.com',
                                [self.buyer.email],
                                fail_silently=False,
                                html_message=html_message
                            )
                        except Exception as e_buyer:
                            print(f"Failed to send order confirmation email to buyer: {e_buyer}")
                        
                        try:
                            # 2. Group items by seller and send order alerts to each seller
                            from collections import defaultdict
                            seller_items = defaultdict(list)
                            for item in items:
                                if item.product and item.product.seller:
                                    seller_items[item.product.seller].append(item)
                            
                            for seller, s_items in seller_items.items():
                                recipient_email = seller.support_email or (seller.user.email if seller.user else None)
                                if recipient_email:
                                    try:
                                        seller_subject = f"[New Order Alert] Order #{self.id} - Action Required"
                                        
                                        # Build text and HTML for the products
                                        items_text = ""
                                        items_html_rows = ""
                                        seller_subtotal = 0.00
                                        
                                        for s_item in s_items:
                                            item_price = float(s_item.price)
                                            item_subtotal = item_price * s_item.quantity
                                            seller_subtotal += item_subtotal
                                            items_text += f"- {s_item.product.name} (Qty: {s_item.quantity}) - ${item_price:.2f} each\n"
                                            
                                            items_html_rows += f"""
                                            <tr>
                                                <td style="padding: 10px; border-bottom: 1px solid #e4e4e7; text-align: left; font-size: 13px; color: #27272a;">{s_item.product.name}</td>
                                                <td style="padding: 10px; border-bottom: 1px solid #e4e4e7; text-align: center; font-size: 13px; color: #27272a;">{s_item.quantity}</td>
                                                <td style="padding: 10px; border-bottom: 1px solid #e4e4e7; text-align: right; font-size: 13px; color: #27272a;">${item_price:.2f}</td>
                                                <td style="padding: 10px; border-bottom: 1px solid #e4e4e7; text-align: right; font-weight: bold; font-size: 13px; color: #18181b;">${item_subtotal:.2f}</td>
                                            </tr>
                                            """
                                        
                                        seller_message = (
                                            f"Hello {seller.shop_name or 'Seller'},\n\n"
                                            f"Good news! You have received a new order on VendorNest.\n\n"
                                            f"Order ID: #{self.id}\n"
                                            f"Payment Method: {self.get_payment_method_display()}\n"
                                            f"Total to receive: ${seller_subtotal:.2f}\n\n"
                                            f"Items to pack:\n{items_text}\n"
                                            f"Shipping Address:\n"
                                            f"Name: {self.shipping_name or self.buyer.username}\n"
                                            f"Phone: {self.shipping_phone or 'N/A'}\n"
                                            f"Address: {self.shipping_address or 'N/A'}, {self.shipping_city or 'N/A'}, Zip {self.shipping_zip or 'N/A'}\n\n"
                                            f"Please package these items immediately and ship them to the buyer using your preferred courier service.\n\n"
                                            f"Best regards,\n"
                                            f"The VendorNest Team"
                                        )
                                        
                                        seller_html = f"""
                                        <!DOCTYPE html>
                                        <html>
                                        <head>
                                            <meta charset="utf-8">
                                        </head>
                                        <body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                            <table cellpadding="0" cellspacing="0" style="width: 100%; padding: 40px 20px; background-color: #f4f4f5;">
                                                <tr>
                                                    <td align="center">
                                                        <table cellpadding="0" cellspacing="0" style="width: 100%; max-width: 600px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e4e4e7; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                                                            <tr>
                                                                <td style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 32px; text-align: center; color: white;">
                                                                    <div style="font-size: 11px; font-weight: 800; color: #c7d2fe; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">Order Notification</div>
                                                                    <h1 style="margin: 0; font-size: 22px; font-weight: 900;">New Order Received!</h1>
                                                                    <div style="font-size: 13px; margin-top: 8px; font-weight: 500; color: #e0e7ff;">Order #{self.id}</div>
                                                                </td>
                                                            </tr>
                                                            <tr>
                                                                <td style="padding: 32px;">
                                                                    <p style="font-size: 15px; color: #27272a; margin-bottom: 20px;">
                                                                        Hello <strong>{seller.shop_name or 'Seller'}</strong>,<br><br>
                                                                        Congratulations! A customer has purchased your product(s) on VendorNest. Please package the items below and ship them to the customer's address as soon as possible.
                                                                    </p>
                                                                    
                                                                    <div style="font-weight: 800; font-size: 11px; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">Items to Pack</div>
                                                                    <table cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                                                                        <thead>
                                                                            <tr style="border-bottom: 2px solid #e4e4e7;">
                                                                                <th style="padding: 8px; text-align: left; font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase;">Product</th>
                                                                                <th style="padding: 8px; text-align: center; font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase; width: 60px;">Qty</th>
                                                                                <th style="padding: 8px; text-align: right; font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase; width: 80px;">Price</th>
                                                                                <th style="padding: 8px; text-align: right; font-size: 11px; font-weight: 800; color: #71717a; text-transform: uppercase; width: 90px;">Total</th>
                                                                            </tr>
                                                                        </thead>
                                                                        <tbody>
                                                                            {items_html_rows}
                                                                        </tbody>
                                                                    </table>
                                                                    
                                                                    <div style="text-align: right; font-size: 14px; color: #4b5563; margin-bottom: 24px;">
                                                                        Your Share Subtotal: <strong style="color: #4f46e5; font-size: 16px;">${seller_subtotal:.2f}</strong>
                                                                    </div>
                                                                    
                                                                    <div style="font-weight: 800; font-size: 11px; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">Customer Shipping Details</div>
                                                                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; font-size: 12px; color: #334155; line-height: 1.6; text-align: left;">
                                                                        <div style="font-weight: 700; color: #1e293b;">{self.shipping_name or self.buyer.username}</div>
                                                                        <div>📞 {self.shipping_phone or 'N/A'}</div>
                                                                        <div style="margin-top: 4px;">📍 {self.shipping_address or 'N/A'}, {self.shipping_city or 'N/A'}, Zip {self.shipping_zip or 'N/A'}</div>
                                                                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e2e8f0; font-weight: 600; color: #0f172a;">
                                                                            Payment Method: {self.get_payment_method_display()}
                                                                        </div>
                                                                    </div>
                                                                    
                                                                    <p style="margin-top: 24px; font-size: 12px; color: #9ca3af; line-height: 1.5; text-align: center;">
                                                                        Please log into your seller panel to update the shipment tracking status once sent.
                                                                    </p>
                                                                </td>
                                                            </tr>
                                                        </table>
                                                    </td>
                                                </tr>
                                            </table>
                                        </body>
                                        </html>
                                        """
                                        
                                        send_mail(
                                            seller_subject,
                                            seller_message,
                                            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vendornest.com',
                                            [recipient_email],
                                            fail_silently=False,
                                            html_message=seller_html
                                        )
                                        print(f"Seller order notification sent successfully to {recipient_email}")
                                    except Exception as e_seller:
                                        print(f"Failed to send order email alert to seller {recipient_email}: {e_seller}")
                        except Exception as e_seller_group:
                            print(f"Failed in seller email grouping/sending: {e_seller_group}")

                    threading.Thread(target=send_async_emails, daemon=True).start()
                    email_updated = True
                except Exception as e:
                    print(f"Failed to initiate background order emails: {e}")
                    
            sms_updated = False
            if not self.sms_sent:
                try:
                    from twilio.rest import Client
                    from django.conf import settings
                    
                    if hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID:
                        phone_to_use = self.shipping_phone or self.buyer.phone_number
                        if phone_to_use:
                            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                            message_body = f"Hello {self.buyer.username}, Your order #{self.id} has been successfully confirmed. Total Amount: ${self.total_amount}. Thank you for shopping with VendorNest!"
                            message = client.messages.create(
                                body=message_body,
                                from_=settings.TWILIO_PHONE_NUMBER,
                                to=str(phone_to_use)
                            )
                            print(f"Twilio SMS sent: {message.sid}")
                            sms_updated = True
                        else:
                            print(f"Order #{self.id} does not have a phone number. Skipping SMS.")
                    else:
                        print("Twilio settings are missing. Skipping SMS.")
                except Exception as e:
                    print(f"Failed to send order confirmation SMS: {e}")
            
            # Update tracked states without calling save() recursively
            if stock_updated or email_updated or sms_updated or ledger_updated:
                Order.objects.filter(pk=self.pk).update(
                    stock_deducted=True if stock_updated else self.stock_deducted,
                    email_sent=True if email_updated else self.email_sent,
                    sms_sent=True if sms_updated else self.sms_sent,
                    ledger_credited=True if ledger_updated else self.ledger_credited
                )

    def __str__(self):
        return f"Order {self.id} by {self.buyer.username}"

class OrderItem(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="order_items")
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"
