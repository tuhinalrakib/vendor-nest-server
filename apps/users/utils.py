import threading
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

# Common footer variables
FOOTER_PLAIN = (
    "\n\n--\n"
    "VendorNest Inc.\n"
    "123 Tech Avenue, Suite 400\n"
    "Dhaka, Bangladesh 1212\n"
    "support@vendornest.com"
)

FOOTER_HTML = """
                <!-- Footer Info -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 500px; text-align: center;">
                    <tr>
                        <td style="padding: 24px 20px 0 20px; font-size: 12px; line-height: 1.5; color: #94a3b8; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                            <strong>VendorNest Inc.</strong><br>
                            123 Tech Avenue, Suite 400<br>
                            Dhaka, Bangladesh 1212<br>
                            <a href="mailto:support@vendornest.com" style="color: #3b82f6; text-decoration: none;">support@vendornest.com</a>
                        </td>
                    </tr>
                </table>
"""

def send_admin_otp_email(user, otp, is_resend=False):
    subject = "Admin Login Verification - New OTP Code" if is_resend else "Admin Login Verification - OTP Code"
    user_name = user.get_full_name() or user.username or "Admin"
    
    # Plain text version for fallback
    if is_resend:
        message = (
            f"Hello {user_name},\n\n"
            f"Your new 2FA verification OTP is: {otp}\n"
            f"This code is valid for 5 minutes.\n\n"
            f"Best regards,\n"
            f"Team VendorNest"
        )
    else:
        message = (
            f"Hello {user_name},\n\n"
            f"A login attempt was made to your admin account on VendorNest.\n\n"
            f"Your 2FA verification OTP is: {otp}\n"
            f"This code is valid for 5 minutes.\n\n"
            f"If you did not request this, please secure your account credentials immediately.\n\n"
            f"Best regards,\n"
            f"Team VendorNest"
        )
    message += FOOTER_PLAIN

    # Beautiful premium HTML version matching requested mockup
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; -webkit-font-smoothing: antialiased;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f9;">
        <tr>
            <td align="center" style="padding: 40px 10px;">
                <!-- Card Container -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 500px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); border: 1px solid #eef2f6; overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td align="center" style="padding: 40px 40px 20px 40px; background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: #ffffff;">
                            <h2 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; font-family: 'Inter', sans-serif; color: #ffffff;">Your One-Time Password</h2>
                            <p style="margin: 8px 0 0 0; font-size: 14px; color: #dbeafe; font-weight: 500;">Admin Security Verification</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px; text-align: left;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #1e293b; font-family: 'Inter', sans-serif;">Dear <strong style="color: #1e3a8a;">{user_name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.6; color: #475569; font-family: 'Inter', sans-serif;">{"Here is your new One-Time Password to securely log in to your admin account:" if is_resend else "A login attempt was made to your admin account on <strong>VendorNest</strong>. Here is your One-Time Password to securely log in to your account:"}</p>
                            
                            <!-- OTP Box -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; text-align: center; margin: 28px 0;">
                                <span style="display: block; font-family: 'Courier New', Courier, monospace; font-size: 42px; font-weight: 800; letter-spacing: 8px; color: #1e3a8a; line-height: 1;">{otp}</span>
                            </div>
                            
                            <p style="margin: 0 0 24px 0; font-size: 13px; text-align: center; color: #64748b; font-weight: 500; font-family: 'Inter', sans-serif;">Note: This OTP is valid for <strong style="color: #1e3a8a;">5 minutes</strong>.</p>
                            
                            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 24px 0;">
                            
                            <p style="margin: 0 0 20px 0; font-size: 13px; line-height: 1.5; color: #94a3b8; font-family: 'Inter', sans-serif;">If you did not request this OTP, please disregard this email or contact our support team immediately to secure your credentials.</p>
                            
                            <p style="margin: 0; font-size: 14px; font-weight: 600; color: #334155; font-family: 'Inter', sans-serif;">Best regards,</p>
                            <p style="margin: 4px 0 0 0; font-size: 14px; font-weight: 700; color: #1e3a8a; font-family: 'Inter', sans-serif;">Team VendorNest</p>
                        </td>
                    </tr>
                </table>
                {FOOTER_HTML}
            </td>
        </tr>
    </table>
</body>
</html>
"""

    def run_send_mail():
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vendornest.com',
                [user.email],
                fail_silently=False,
                html_message=html_message
            )
            logger.info(f"OTP email successfully sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send admin login OTP email to {user.email}: {e}")

    threading.Thread(target=run_send_mail, daemon=True).start()


def send_user_verification_email(user, activation_link):
    subject = "Verify your email - VendorNest"
    user_name = user.get_full_name() or user.username or "User"
    
    # Plain text version for fallback
    message = (
        f"Hello {user_name},\n\n"
        f"Please verify your email by clicking the link below:\n"
        f"{activation_link}\n\n"
        f"Thank you!\n"
        f"Team VendorNest"
    )
    message += FOOTER_PLAIN

    # HTML Version
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; -webkit-font-smoothing: antialiased;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f9;">
        <tr>
            <td align="center" style="padding: 40px 10px;">
                <!-- Card Container -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 500px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); border: 1px solid #eef2f6; overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td align="center" style="padding: 40px 40px 20px 40px; background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #ffffff;">
                            <h2 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; font-family: 'Inter', sans-serif; color: #ffffff;">Verify Your Email</h2>
                            <p style="margin: 8px 0 0 0; font-size: 14px; color: #e0e7ff; font-weight: 500;">Welcome to VendorNest</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px; text-align: left;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #1e293b; font-family: 'Inter', sans-serif;">Hello {user_name},</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.6; color: #475569; font-family: 'Inter', sans-serif;">Thank you for registering on <strong>VendorNest</strong>. Please verify your email address to activate your account and access all our platform features:</p>
                            
                            <!-- CTA Button -->
                            <div style="text-align: center; margin: 32px 0;">
                                <a href="{activation_link}" style="display: inline-block; background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%); color: #ffffff; text-decoration: none; padding: 14px 36px; border-radius: 12px; font-size: 14px; font-weight: 700; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2); transition: all 0.2s;">
                                    Verify Email Address
                                </a>
                            </div>
                            
                            <p style="margin: 0 0 8px 0; font-size: 12px; color: #94a3b8; font-family: 'Inter', sans-serif;">Or copy and paste this link into your browser:</p>
                            <p style="margin: 0 0 24px 0; font-size: 12px; word-break: break-all; color: #3b82f6; font-family: 'Inter', sans-serif;"><a href="{activation_link}" style="color: #3b82f6; text-decoration: none;">{activation_link}</a></p>
                            
                            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 24px 0;">
                            
                            <p style="margin: 0; font-size: 14px; font-weight: 600; color: #334155; font-family: 'Inter', sans-serif;">Best regards,</p>
                            <p style="margin: 4px 0 0 0; font-size: 14px; font-weight: 700; color: #4f46e5; font-family: 'Inter', sans-serif;">Team VendorNest</p>
                        </td>
                    </tr>
                </table>
                {FOOTER_HTML}
            </td>
        </tr>
    </table>
</body>
</html>
"""

    def run_send_mail():
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vendornest.com',
                [user.email],
                fail_silently=False,
                html_message=html_message
            )
            logger.info(f"Verification email successfully sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")

    threading.Thread(target=run_send_mail, daemon=True).start()


def send_seller_approval_email(user, shop_name, subdomain):
    subject = "Your Seller Application has been Approved! - VendorNest"
    user_name = user.get_full_name() or user.username or "Seller"
    
    # Plain text version for fallback
    message = (
        f"Hello {user_name},\n\n"
        f"Congratulations! Your seller application for '{shop_name or 'your shop'}' on VendorNest "
        f"has been approved by our administrators.\n\n"
        f"You can now access your seller dashboard, manage your store settings, and list products in our catalog.\n"
        f"Your store subdomain: {subdomain or 'not-set'}.vendornest.com\n\n"
        f"Thank you for choosing VendorNest!\n\n"
        f"Best regards,\n"
        f"The VendorNest Team"
    )
    message += FOOTER_PLAIN

    # HTML Version
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; -webkit-font-smoothing: antialiased;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f9;">
        <tr>
            <td align="center" style="padding: 40px 10px;">
                <!-- Card Container -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 500px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); border: 1px solid #eef2f6; overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td align="center" style="padding: 40px 40px 20px 40px; background: linear-gradient(135deg, #10b981, #059669); color: #ffffff;">
                            <h2 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; font-family: 'Inter', sans-serif; color: #ffffff;">Application Approved!</h2>
                            <p style="margin: 8px 0 0 0; font-size: 14px; color: #d1fae5; font-weight: 500;">Welcome to VendorNest Merchant Network</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px; text-align: left;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #1e293b; font-family: 'Inter', sans-serif;">Hello {user_name},</p>
                            <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6; color: #475569; font-family: 'Inter', sans-serif;">Congratulations! Your seller application for <strong>'{shop_name or "your shop"}'</strong> has been approved by our administrators.</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.6; color: #475569; font-family: 'Inter', sans-serif;">You can now manage store settings, list products in our catalog, and view analytical insights on your merchant dashboard.</p>
                            
                            <div style="background-color: #ecfdf5; border: 1px solid #d1fae5; border-radius: 12px; padding: 16px; margin: 24px 0; font-size: 14px; color: #065f46;">
                                <strong>Your Shop Details:</strong><br>
                                <span style="display: inline-block; margin-top: 4px;">Subdomain: <strong>{subdomain or "not-set"}.vendornest.com</strong></span>
                            </div>
                            
                            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 24px 0;">
                            
                            <p style="margin: 0; font-size: 14px; font-weight: 600; color: #334155; font-family: 'Inter', sans-serif;">Best regards,</p>
                            <p style="margin: 4px 0 0 0; font-size: 14px; font-weight: 700; color: #10b981; font-family: 'Inter', sans-serif;">Team VendorNest</p>
                        </td>
                    </tr>
                </table>
                {FOOTER_HTML}
            </td>
        </tr>
    </table>
</body>
</html>
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=html_message,
        )
        logger.info(f"Successfully sent approval email to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send approval email to {user.email}: {e}")


def send_stock_alert_email(recipient_email, shop_name, product_name, sku, new_stock, is_out_of_stock=False):
    subject = f"[Alert] Product Out of Stock: {product_name}" if is_out_of_stock else f"[Alert] Low Stock Warning: {product_name}"
    
    if is_out_of_stock:
        message = (
            f"Hello {shop_name or 'Seller'},\n\n"
            f"Your product '{product_name}' (SKU: {sku}) is now OUT OF STOCK.\n\n"
            f"Please update your stock in the seller inventory panel immediately to resume sales.\n\n"
            f"Best regards,\n"
            f"VendorNest Platform"
        )
    else:
        message = (
            f"Hello {shop_name or 'Seller'},\n\n"
            f"Your product '{product_name}' (SKU: {sku}) is running low on stock.\n\n"
            f"Current stock: {new_stock} units (below the 8 units threshold).\n\n"
            f"Please restock this item soon.\n\n"
            f"Best regards,\n"
            f"VendorNest Platform"
        )
    message += FOOTER_PLAIN

    # HTML Version
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; -webkit-font-smoothing: antialiased;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f9;">
        <tr>
            <td align="center" style="padding: 40px 10px;">
                <!-- Card Container -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 500px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); border: 1px solid #eef2f6; overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td align="center" style="padding: 40px 40px 20px 40px; background: linear-gradient(135deg, {"#ef4444, #dc2626" if is_out_of_stock else "#f59e0b, #d97706"}); color: #ffffff;">
                            <h2 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; font-family: 'Inter', sans-serif; color: #ffffff;">{"Out of Stock!" if is_out_of_stock else "Low Stock Warning"}</h2>
                            <p style="margin: 8px 0 0 0; font-size: 14px; color: {"#fee2e2" if is_out_of_stock else "#fef3c7"}; font-weight: 500;">Inventory Alert System</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px; text-align: left;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #1e293b; font-family: 'Inter', sans-serif;">Hello {shop_name or 'Seller'},</p>
                            <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6; color: #475569; font-family: 'Inter', sans-serif;">
                                {"Your product has run out of stock and is currently unavailable for buyers to purchase." if is_out_of_stock else "Your product stock is dropping below the alert threshold (8 units)."}
                            </p>
                            
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin: 24px 0; font-size: 14px; color: #334155;">
                                <strong>Product Details:</strong><br>
                                <span style="display: inline-block; margin-top: 4px;">Name: <strong>{product_name}</strong></span><br>
                                <span>SKU: <strong>{sku or "N/A"}</strong></span><br>
                                <span>Current Stock: <strong style="color: {"#ef4444" if is_out_of_stock else "#f59e0b"};">{new_stock} units</strong></span>
                            </div>
                            
                            <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.6; color: #475569; font-family: 'Inter', sans-serif;">Please login to your seller portal to update stock quantities and resume normal sales.</p>
                            
                            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 24px 0;">
                            
                            <p style="margin: 0; font-size: 14px; font-weight: 600; color: #334155; font-family: 'Inter', sans-serif;">Best regards,</p>
                            <p style="margin: 4px 0 0 0; font-size: 14px; font-weight: 700; color: #4f46e5; font-family: 'Inter', sans-serif;">VendorNest Platform</p>
                        </td>
                    </tr>
                </table>
                {FOOTER_HTML}
            </td>
        </tr>
    </table>
</body>
</html>
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=True,
            html_message=html_message,
        )
        logger.info(f"Successfully sent stock alert email to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send stock alert email to {recipient_email}: {e}")
