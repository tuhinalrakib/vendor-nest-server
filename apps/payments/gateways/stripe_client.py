import uuid
import logging
import urllib.request
import urllib.parse
import json
from django.conf import settings

logger = logging.getLogger(__name__)

class StripeSandboxClient:
    @staticmethod
    def create_checkout_session(order_id, amount, success_url, cancel_url):
        stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_mock_secret_key')
        
        if stripe_key and not stripe_key.startswith('sk_test_mock_'):
            try:
                amount_cents = int(float(amount) * 100)
                url = "https://api.stripe.com/v1/checkout/sessions"
                
                # Prepare urlencoded request parameters
                data = {
                    'payment_method_types[0]': 'card',
                    'line_items[0][price_data][currency]': 'usd',
                    'line_items[0][price_data][product_data][name]': f'Order {order_id}',
                    'line_items[0][price_data][unit_amount]': str(amount_cents),
                    'line_items[0][quantity]': '1',
                    'mode': 'payment',
                    'success_url': success_url,
                    'cancel_url': cancel_url,
                    'client_reference_id': str(order_id)
                }
                
                req_data = urllib.parse.urlencode(data).encode('utf-8')
                req = urllib.request.Request(url, data=req_data, method='POST')
                req.add_header('Authorization', f'Bearer {stripe_key}')
                req.add_header('Content-Type', 'application/x-www-form-urlencoded')
                
                with urllib.request.urlopen(req) as response:
                    res_body = response.read().decode('utf-8')
                    session = json.loads(res_body)
                    logger.info(f"Successfully created Stripe Checkout Session: {session.get('id')}")
                    return {
                        "id": session.get("id"),
                        "checkout_url": session.get("url"),
                        "is_sandbox": False
                    }
            except Exception as e:
                logger.error(f"Failed to create real Stripe Checkout Session via urllib: {e}")
                
        tx_id = f"cs_mock_{uuid.uuid4().hex[:16]}"
        checkout_url = f"http://127.0.0.1:8000/api/payments/stripe/verify/?session_id={tx_id}&order_id={order_id}&status=success"
        logger.info(f"Simulating Stripe Checkout Session in Sandbox Mode. Order: {order_id}, Amount: {amount}")
        
        return {
            "id": tx_id,
            "checkout_url": checkout_url,
            "is_sandbox": True
        }

    @staticmethod
    def verify_payment(session_id):
        stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_mock_secret_key')
        
        if stripe_key and not stripe_key.startswith('sk_test_mock_') and not session_id.startswith('cs_mock_'):
            try:
                url = f"https://api.stripe.com/v1/checkout/sessions/{session_id}"
                req = urllib.request.Request(url, method='GET')
                req.add_header('Authorization', f'Bearer {stripe_key}')
                
                with urllib.request.urlopen(req) as response:
                    res_body = response.read().decode('utf-8')
                    session = json.loads(res_body)
                    if session.get("payment_status") == "paid":
                        return {
                            "status": "succeeded",
                            "charge_id": session.get("payment_intent"),
                            "order_id": session.get("client_reference_id")
                        }
            except Exception as e:
                logger.error(f"Failed to verify Stripe session via urllib: {e}")
                
        return {
            "status": "succeeded",
            "charge_id": f"ch_mock_{uuid.uuid4().hex[:12]}",
            "order_id": None
        }
