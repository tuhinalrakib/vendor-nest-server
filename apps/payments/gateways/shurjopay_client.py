import uuid
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class ShurjopaySandboxClient:
    @staticmethod
    def get_token():
        return {
            "token": f"sp_token_{uuid.uuid4().hex}",
            "store_id": "vendornest_mock_store",
        }

    @staticmethod
    def initiate_payment(amount, return_url, cancel_url):
        tx_id = f"sp_mock_tx_{uuid.uuid4().hex[:16]}"
        # Mocking the Shurjopay hosted checkout redirect URL
        # For simplicity, we redirect the client back to our callback endpoint with success parameters
        checkout_url = f"{settings.BACKEND_URL}/api/payments/shurjopay/callback/?sp_tx_id={tx_id}&status=success"
        logger.info(f"Simulating Shurjopay payment initiation. Amount: {amount}")
        return {
            "checkout_url": checkout_url,
            "sp_tx_id": tx_id,
            "status": "initiated"
        }

    @staticmethod
    def verify_payment(sp_tx_id):
        logger.info(f"Simulating Shurjopay transaction query verification for: {sp_tx_id}")
        return {
            "status": "success",
            "sp_tx_id": sp_tx_id,
            "bank_tx_id": f"bank_mock_{uuid.uuid4().hex[:12]}",
            "message": "Transaction verified successfully"
        }
