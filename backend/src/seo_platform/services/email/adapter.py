"""
SEO Platform — Email Adapter
=============================
Pluggable email architecture. Supports local Mailhog for zero-cost dev.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

class EmailAdapter:
    def __init__(self):
        self.settings = get_settings()

    def send_email(self, to_email: str, subject: str, body: str):
        """Sends an email via the configured SMTP server (Mailhog)."""
        msg = MIMEMultipart()
        msg['From'] = "ops@buildit.local"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.send_message(msg)
            logger.info("email_sent_success", to=to_email)
        except Exception as e:
            logger.error("email_sent_failed", error=str(e))
            # In dev/mock mode, we don't necessarily want to fail the workflow
            if self.settings.app_env != "production":
                logger.warning("email_failure_suppressed_in_dev")
            else:
                raise

email_adapter = EmailAdapter()
