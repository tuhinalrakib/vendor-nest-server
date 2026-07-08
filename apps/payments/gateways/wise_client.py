import os
import uuid
import logging
import requests

logger = logging.getLogger(__name__)

WISE_SANDBOX_URL = "https://api.sandbox.transferwise.tech"
WISE_API_TOKEN = os.getenv("WISE_API_TOKEN")
WISE_PROFILE_ID = os.getenv("WISE_PROFILE_ID")

class WiseSandboxClient:
    @staticmethod
    def _get_headers():
        if not WISE_API_TOKEN:
            return None
        return {
            "Authorization": f"Bearer {WISE_API_TOKEN}",
            "Content-Type": "application/json"
        }

    @staticmethod
    def create_recipient(name, account_details):
        headers = WiseSandboxClient._get_headers()
        if not headers or not WISE_PROFILE_ID:
            logger.warning("Wise credentials missing (WISE_API_TOKEN or WISE_PROFILE_ID). Using simulation.")
            return {
                "id": f"rec_sim_{uuid.uuid4().hex[:12]}",
                "name": name,
                "details": account_details
            }

        # Detect account type: if email, use email. Otherwise assume IBAN.
        is_email = "@" in str(account_details)
        payload = {
            "profile": int(WISE_PROFILE_ID),
            "accountHolderName": name,
            "currency": "USD" if is_email else "EUR", # Fallback currencies
            "type": "email" if is_email else "iban",
            "details": {
                "email": account_details
            } if is_email else {
                "iban": account_details
            }
        }

        try:
            response = requests.post(f"{WISE_SANDBOX_URL}/v1/accounts", json=payload, headers=headers)
            if response.status_code in [200, 201]:
                res_data = response.json()
                return {
                    "id": str(res_data.get("id")),
                    "name": res_data.get("accountHolderName"),
                    "details": account_details
                }
            else:
                logger.error(f"Wise API Error creating recipient: {response.text}")
        except Exception as e:
            logger.error(f"Failed to call Wise API: {str(e)}")

        # Fallback
        return {
            "id": f"rec_sim_err_{uuid.uuid4().hex[:12]}",
            "name": name,
            "details": account_details
        }

    @staticmethod
    def create_quote(source_currency, target_currency, amount):
        headers = WiseSandboxClient._get_headers()
        if not headers or not WISE_PROFILE_ID:
            logger.warning("Wise credentials missing. Using simulation.")
            return {
                "id": f"qte_sim_{uuid.uuid4().hex[:12]}",
                "source": source_currency,
                "target": target_currency,
                "sourceAmount": amount,
                "targetAmount": str(float(amount) * 0.98),
                "rate": "1.00",
                "fee": "2.50"
            }

        payload = {
            "profile": int(WISE_PROFILE_ID),
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "sourceAmount": float(amount)
        }

        try:
            response = requests.post(f"{WISE_SANDBOX_URL}/v2/quotes", json=payload, headers=headers)
            if response.status_code in [200, 201]:
                res_data = response.json()
                return {
                    "id": str(res_data.get("id")),
                    "source": res_data.get("sourceCurrency"),
                    "target": res_data.get("targetCurrency"),
                    "sourceAmount": str(res_data.get("sourceAmount")),
                    "targetAmount": str(res_data.get("targetAmount")),
                    "rate": str(res_data.get("rate")),
                    "fee": str(res_data.get("fee", {}).get("transferwise", 0))
                }
            else:
                logger.error(f"Wise API Error creating quote: {response.text}")
        except Exception as e:
            logger.error(f"Failed to call Wise API: {str(e)}")

        return {
            "id": f"qte_sim_err_{uuid.uuid4().hex[:12]}",
            "source": source_currency,
            "target": target_currency,
            "sourceAmount": amount,
            "targetAmount": str(float(amount) * 0.98),
            "rate": "1.00",
            "fee": "2.50"
        }

    @staticmethod
    def create_transfer(recipient_id, quote_id, reference):
        headers = WiseSandboxClient._get_headers()
        if not headers:
            logger.warning("Wise credentials missing. Using simulation.")
            return {
                "id": f"trf_sim_{uuid.uuid4().hex[:16]}",
                "recipientId": recipient_id,
                "quoteId": quote_id,
                "status": "processing",
                "reference": reference,
                "message": "Wise transfer simulated successfully."
            }

        payload = {
            "targetAccount": int(recipient_id) if recipient_id.isdigit() else 1234567,
            "quoteUuid": quote_id,
            "customerTransactionId": str(uuid.uuid4()),
            "details": {
                "reference": reference
            }
        }

        try:
            response = requests.post(f"{WISE_SANDBOX_URL}/v1/transfers", json=payload, headers=headers)
            if response.status_code in [200, 201]:
                res_data = response.json()
                return {
                    "id": str(res_data.get("id")),
                    "recipientId": str(res_data.get("targetAccount")),
                    "quoteId": str(res_data.get("quoteUuid")),
                    "status": res_data.get("status", "processing"),
                    "reference": reference,
                    "message": "Wise transfer created successfully."
                }
            else:
                logger.error(f"Wise API Error creating transfer: {response.text}")
        except Exception as e:
            logger.error(f"Failed to call Wise API: {str(e)}")

        return {
            "id": f"trf_sim_err_{uuid.uuid4().hex[:16]}",
            "recipientId": recipient_id,
            "quoteId": quote_id,
            "status": "failed",
            "reference": reference,
            "message": "Wise transfer creation failed, fell back to simulated failed status."
        }
