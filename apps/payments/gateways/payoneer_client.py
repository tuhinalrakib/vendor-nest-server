import uuid
import logging

logger = logging.getLogger(__name__)

class PayoneerSandboxClient:
    @staticmethod
    def verify_recipient(email):
        logger.info(f"Simulating Payoneer Recipient verification: {email}")
        return {
            "status": "active",
            "payoneer_id": f"payoneer_acc_{uuid.uuid4().hex[:12]}",
            "email": email,
        }

    @staticmethod
    def initiate_payout(payoneer_id, amount, reference):
        payout_id = f"pay_mock_{uuid.uuid4().hex[:16]}"
        logger.info(f"Simulating Payoneer Payout. ID: {payout_id}, Account: {payoneer_id}, Amount: {amount}")
        return {
            "payout_id": payout_id,
            "status": "completed",
            "amount": amount,
            "reference": reference,
            "message": "Payoneer payout completed successfully."
        }
