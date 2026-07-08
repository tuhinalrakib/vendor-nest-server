import uuid
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class ShurjopaySandboxClient:
    BASE_URL = "https://sandbox.shurjopayment.com/api"
    USERNAME = "sp_sandbox"
    PASSWORD = "pyyk97hu&6u6"
    PREFIX = "NOK"

    @classmethod
    def get_token(cls):
        try:
            url = f"{cls.BASE_URL}/get_token"
            payload = {
                "username": cls.USERNAME,
                "password": cls.PASSWORD
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # The token is usually returned directly or in a list
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
                
            return {
                "token": data.get("token"),
                "store_id": data.get("store_id"),
                "sp_code": data.get("sp_code"),
                "message": data.get("message")
            }
        except Exception as e:
            logger.error(f"Failed to get Shurjopay token: {str(e)}")
            return None

    @classmethod
    def initiate_payment(cls, amount, return_url, cancel_url, order):
        # 1. Get Authentication Token
        token_data = cls.get_token()
        if not token_data or not token_data.get("token"):
            logger.error("Could not obtain Shurjopay token for transaction.")
            return {
                "checkout_url": cancel_url,
                "sp_tx_id": f"sp_failed_{uuid.uuid4().hex[:12]}",
                "status": "failed",
                "error": "Authentication failed"
            }

        token = token_data["token"]
        store_id = token_data["store_id"]

        # Generate unique order_id that starts with PREFIX "NOK"
        # Shurjopay requires this starting prefix
        tx_id = f"{cls.PREFIX}{uuid.uuid4().hex[:16]}"

        # Gather customer details from order
        customer_name = order.shipping_name or order.buyer.get_full_name() or order.buyer.username or "Customer"
        customer_phone = order.shipping_phone or "01700000000"
        customer_email = order.buyer.email or "customer@example.com"
        customer_address = order.shipping_address or "Dhaka"
        customer_city = order.shipping_city or "Dhaka"
        customer_post_code = order.shipping_zip or "1200"

        payload = {
            "prefix": cls.PREFIX,
            "token": token,
            "return_url": return_url,
            "cancel_url": cancel_url,
            "store_id": store_id,
            "amount": float(amount),
            "order_id": tx_id,
            "currency": "BDT",
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "customer_address": customer_address,
            "customer_city": customer_city,
            "customer_post_code": customer_post_code,
            "customer_country": "Bangladesh",
            "client_ip": "127.0.0.1"
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            url = f"{cls.BASE_URL}/secret-pay"
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            res_data = response.json()

            if isinstance(res_data, list) and len(res_data) > 0:
                res_data = res_data[0]

            checkout_url = res_data.get("checkout_url")
            if checkout_url:
                logger.info(f"Successfully initiated Shurjopay transaction {tx_id}. Checkout URL: {checkout_url}")
                return {
                    "checkout_url": checkout_url,
                    "sp_tx_id": tx_id,
                    "status": "initiated"
                }
            else:
                logger.error(f"Shurjopay response missing checkout_url: {res_data}")
                return {
                    "checkout_url": cancel_url,
                    "sp_tx_id": tx_id,
                    "status": "failed",
                    "error": res_data.get("message", "Initiation failed")
                }
        except Exception as e:
            logger.error(f"Failed to initiate Shurjopay payment: {str(e)}")
            return {
                "checkout_url": cancel_url,
                "sp_tx_id": tx_id,
                "status": "failed",
                "error": str(e)
            }

    @classmethod
    def verify_payment(cls, sp_tx_id):
        token_data = cls.get_token()
        if not token_data or not token_data.get("token"):
            logger.error("Could not obtain Shurjopay token for verification.")
            return {
                "status": "failed",
                "message": "Token authentication failed"
            }

        token = token_data["token"]
        url = f"{cls.BASE_URL}/verification"
        payload = {
            "order_id": sp_tx_id
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            res_data = response.json()

            if isinstance(res_data, list) and len(res_data) > 0:
                res_data = res_data[0]

            sp_code = res_data.get("sp_code")
            if str(sp_code) == "1000":
                logger.info(f"Shurjopay transaction verified successfully: {sp_tx_id}")
                return {
                    "status": "success",
                    "sp_tx_id": sp_tx_id,
                    "bank_tx_id": res_data.get("bank_tx_id") or res_data.get("bank_trx_id"),
                    "message": res_data.get("message") or res_data.get("sp_message") or "Transaction verified successfully"
                }
            else:
                logger.warning(f"Shurjopay transaction verification failed: {sp_tx_id}. Code: {sp_code}, Response: {res_data}")
                return {
                    "status": "failed",
                    "message": res_data.get("message") or res_data.get("sp_message") or f"Verification failed with code {sp_code}"
                }
        except Exception as e:
            logger.error(f"Failed to verify Shurjopay transaction {sp_tx_id}: {str(e)}")
            return {
                "status": "failed",
                "message": str(e)
            }

