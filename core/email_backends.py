import requests
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

class ResendEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, 'RESEND_API_KEY', None)
        self.api_url = "https://api.resend.com/emails"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY is not set in Django settings.")
            logger.error("RESEND_API_KEY is missing. Cannot send email.")
            return 0

        sent_count = 0
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        for message in email_messages:
            try:
                # Prepare Resend JSON payload
                payload = {
                    "from": message.from_email,
                    "to": message.to,
                    "subject": message.subject,
                }
                
                # Check for HTML and plain text alternatives
                if isinstance(message, EmailMultiAlternatives):
                    payload["text"] = message.body
                    for content, mimetype in message.alternatives:
                        if mimetype == "text/html":
                            payload["html"] = content
                            break
                else:
                    # If html content subtype is specified directly
                    if getattr(message, 'content_subtype', None) == 'html':
                        payload["html"] = message.body
                    else:
                        payload["text"] = message.body

                # Call Resend REST API
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
                
                if response.status_code in [200, 201]:
                    sent_count += 1
                else:
                    error_data = response.json() if response.content else response.text
                    logger.error(f"Resend API error: {response.status_code} - {error_data}")
                    if not self.fail_silently:
                        response.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to send email via Resend: {e}")
                if not self.fail_silently:
                    raise
        return sent_count


class BrevoEmailBackend(BaseEmailBackend):
    """
    Custom email backend to send emails via Brevo (formerly Sendinblue) HTTP API.
    Does not require a custom domain; you can use your verified Gmail as sender.
    """
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        import os
        self.api_key = getattr(settings, 'BREVO_API_KEY', None) or os.getenv('BREVO_API_KEY')
        self.api_url = "https://api.brevo.com/v3/smtp/email"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError("BREVO_API_KEY is not set in Django settings.")
            logger.error("BREVO_API_KEY is missing. Cannot send email.")
            return 0

        sent_count = 0
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VendorNest/1.0"
        }

        # Create persistent session to avoid TLS handshake EOF errors
        session = requests.Session()
        session.headers.update(headers)

        for message in email_messages:
            try:
                # Brevo API format
                sender_email = message.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'eng.tuhin77@gmail.com')
                payload = {
                    "sender": {
                        "name": "VendorNest",
                        "email": sender_email
                    },
                    "to": [{"email": r} for r in message.to],
                    "subject": message.subject,
                }
                
                # Extract plain text and html bodies
                if isinstance(message, EmailMultiAlternatives):
                    payload["textContent"] = message.body
                    for content, mimetype in message.alternatives:
                        if mimetype == "text/html":
                            payload["htmlContent"] = content
                            break
                else:
                    if getattr(message, 'content_subtype', None) == 'html':
                        payload["htmlContent"] = message.body
                    else:
                        payload["textContent"] = message.body

                # Send POST request to Brevo API using persistent session
                response = session.post(self.api_url, json=payload, timeout=10)
                
                if response.status_code in [200, 201, 202]:
                    sent_count += 1
                else:
                    error_data = response.json() if response.content else response.text
                    logger.error(f"Brevo API error: {response.status_code} - {error_data}")
                    if not self.fail_silently:
                        response.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to send email via Brevo: {e}")
                if not self.fail_silently:
                    raise
        return sent_count


class FallbackEmailBackend(BaseEmailBackend):
    """
    Smart Email Backend with Automatic Fallback Chain:
    1. Brevo HTTP API
    2. Resend HTTP API
    3. Gmail SMTP
    """
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        from django.core.mail.backends.smtp import EmailBackend as SmtpBackend
        self.brevo_backend = BrevoEmailBackend(fail_silently=True, **kwargs)
        self.resend_backend = ResendEmailBackend(fail_silently=True, **kwargs)
        self.smtp_backend = SmtpBackend(fail_silently=True, **kwargs)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        # Try 1: Brevo HTTP API
        try:
            sent = self.brevo_backend.send_messages(email_messages)
            if sent > 0:
                return sent
        except Exception as e:
            logger.warning(f"Brevo API failed: {e}. Trying Resend API...")

        # Try 2: Resend HTTP API
        try:
            sent = self.resend_backend.send_messages(email_messages)
            if sent > 0:
                return sent
        except Exception as e:
            logger.warning(f"Resend API failed: {e}. Trying SMTP...")

        # Try 3: SMTP
        try:
            sent = self.smtp_backend.send_messages(email_messages)
            if sent > 0:
                return sent
        except Exception as e:
            logger.warning(f"SMTP failed: {e}")

        # Fallback logging if debug mode
        if getattr(settings, 'DEBUG', False):
            for msg in email_messages:
                logger.info(f"[DEV EMAIL LOG] Subject: {msg.subject} | Body: {msg.body}")
            return len(email_messages)

        if not self.fail_silently:
            raise RuntimeError("All configured email backends (Brevo, Resend, SMTP) failed to send email.")
        return 0


