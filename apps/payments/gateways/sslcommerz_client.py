import uuid
import logging
import requests

logger = logging.getLogger(__name__)

class SSLCommerzSandboxClient:
    BASE_URL = "https://sandbox.sslcommerz.com"
    STORE_ID = "rafis693032a1f3cbf"
    STORE_PASS = "rafis693032a1f3cbf@ssl"

    @classmethod
    def initiate_payment(cls, amount, success_url, fail_url, cancel_url, order):
        tx_id = f"ssl_{uuid.uuid4().hex[:16]}"
        
        customer_name = order.shipping_name or order.buyer.get_full_name() or order.buyer.username or "Customer"
        customer_phone = order.shipping_phone or "01700000000"
        customer_email = order.buyer.email or "customer@example.com"
        customer_address = order.shipping_address or "Dhaka"
        customer_city = order.shipping_city or "Dhaka"
        customer_post_code = order.shipping_zip or "1200"

        payload = {
            "store_id": cls.STORE_ID,
            "store_passwd": cls.STORE_PASS,
            "total_amount": float(amount),
            "currency": "BDT",
            "tran_id": tx_id,
            "success_url": success_url,
            "fail_url": fail_url,
            "cancel_url": cancel_url,
            "cus_name": customer_name,
            "cus_email": customer_email,
            "cus_phone": customer_phone,
            "cus_add1": customer_address,
            "cus_city": customer_city,
            "cus_postcode": customer_post_code,
            "cus_country": "Bangladesh",
            "shipping_method": "NO",
            "num_of_item": 1,
            "product_name": f"Order #{order.id}",
            "product_category": "E-Commerce",
            "product_profile": "general"
        }

        try:
            url = f"{cls.BASE_URL}/gwprocess/v4/api.php"
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            res_data = response.json()

            status = res_data.get("status")
            if status == "SUCCESS":
                checkout_url = res_data.get("GatewayPageURL")
                logger.info(f"Successfully initiated SSLCommerz transaction {tx_id}. Checkout URL: {checkout_url}")
                return {
                    "checkout_url": checkout_url,
                    "ssl_tx_id": tx_id,
                    "status": "initiated"
                }
            else:
                logger.error(f"SSLCommerz response missing or failed: {res_data}")
                return {
                    "checkout_url": cancel_url,
                    "ssl_tx_id": tx_id,
                    "status": "failed",
                    "error": res_data.get("failedreason", "Initiation failed")
                }
        except Exception as e:
            logger.error(f"Failed to initiate SSLCommerz payment: {str(e)}")
            return {
                "checkout_url": cancel_url,
                "ssl_tx_id": tx_id,
                "status": "failed",
                "error": str(e)
            }

    @classmethod
    def verify_payment(cls, val_id):
        url = f"{cls.BASE_URL}/validator/api/validationserverAPI.php"
        params = {
            "val_id": val_id,
            "store_id": cls.STORE_ID,
            "store_passwd": cls.STORE_PASS,
            "format": "json"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            res_data = response.json()

            status = res_data.get("status")
            if status in ["VALID", "VALIDATED"]:
                logger.info(f"SSLCommerz transaction verified successfully: val_id={val_id}")
                return {
                    "status": "success",
                    "val_id": val_id,
                    "bank_tx_id": res_data.get("bank_tran_id"),
                    "tran_id": res_data.get("tran_id"),
                    "amount": res_data.get("amount")
                }
            else:
                logger.warning(f"SSLCommerz transaction verification failed: val_id={val_id}. Status: {status}, Response: {res_data}")
                return {
                    "status": "failed",
                    "message": res_data.get("failedreason") or f"Verification failed with status {status}"
                }
        except Exception as e:
            logger.error(f"Failed to verify SSLCommerz transaction val_id={val_id}: {str(e)}")
            return {
                "status": "failed",
                "message": str(e)
            }
