import uuid
import logging

logger = logging.getLogger(__name__)

class WiseSandboxClient:
    @staticmethod
    def create_recipient(name, account_details):
        logger.info(f"Simulating Wise Recipient creation for: {name}")
        return {
            "id": f"rec_{uuid.uuid4().hex[:12]}",
            "name": name,
            "details": account_details
        }

    @staticmethod
    def create_quote(source_currency, target_currency, amount):
        logger.info(f"Simulating Wise Quote. Amount: {amount} {source_currency} -> {target_currency}")
        return {
            "id": f"qte_{uuid.uuid4().hex[:12]}",
            "source": source_currency,
            "target": target_currency,
            "sourceAmount": amount,
            "targetAmount": str(float(amount) * 0.98),
            "rate": "1.00",
            "fee": "2.50"
        }

    @staticmethod
    def create_transfer(recipient_id, quote_id, reference):
        transfer_id = f"trf_mock_{uuid.uuid4().hex[:16]}"
        logger.info(f"Simulating Wise Transfer execution. ID: {transfer_id}, Recipient: {recipient_id}")
        return {
            "id": transfer_id,
            "recipientId": recipient_id,
            "quoteId": quote_id,
            "status": "processing",
            "reference": reference,
            "message": "Wise transfer initiated successfully."
        }
