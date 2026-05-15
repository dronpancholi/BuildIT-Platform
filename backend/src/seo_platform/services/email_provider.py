"""
SEO Platform — Email Provider Abstraction
===========================================
Enterprise abstraction layer that toggles between production delivery APIs
(SendGrid/Mailgun) and local SMTP mocks (Mailhog).
"""

from abc import ABC, abstractmethod
from typing import Any

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

class EmailProvider(ABC):
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: str = "",
        tenant_id: str = "",
        prospect_id: str = "",
    ) -> dict[str, Any]:
        pass


class SendGridProvider(EmailProvider):
    """PRODUCTION: Real SendGrid API integration with delivery tracking."""

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: str = "",
        tenant_id: str = "",
        prospect_id: str = "",
    ) -> dict[str, Any]:

        import httpx
        settings = get_settings()

        logger.info("sendgrid_api_call", to=to_email, campaign_id=campaign_id)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {settings.sendgrid_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "personalizations": [{"to": [{"email": to_email}]}],
                        "from": {"email": settings.sendgrid_sender_email, "name": "SEO Platform"},
                        "subject": subject,
                        "content": [{"type": "text/html", "value": body}],
                    },
                )
                response.raise_for_status()
                logger.info("sendgrid_email_sent", to=to_email)

                await self._track_email(
                    tenant_id, campaign_id, prospect_id, to_email, subject, body, "sent"
                )

                return {"success": True, "message_id": campaign_id, "status": "sent"}
        except Exception as e:
            logger.error("sendgrid_send_failed", to=to_email, error=str(e))
            await self._track_email(
                tenant_id, campaign_id, prospect_id, to_email, subject, body, "failed", str(e)
            )
            return {"success": False, "error": str(e), "status": "failed"}

    async def _track_email(
        self, tenant_id: str, campaign_id: str, prospect_id: str,
        to_email: str, subject: str, body: str, status: str, error: str = None,
    ) -> None:
        if not tenant_id:
            return
        try:
            from datetime import datetime, timezone
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.communication import OutreachEmail, EmailStatus
            from uuid import UUID as PyUUID
            
            async with get_tenant_session(PyUUID(tenant_id)) as session:
                email = OutreachEmail(
                    tenant_id=PyUUID(tenant_id),
                    campaign_id=PyUUID(campaign_id) if campaign_id and campaign_id != "none" else None,
                    prospect_id=prospect_id or to_email,
                    to_email=to_email,
                    subject=subject,
                    body_html=body,
                    status=EmailStatus(status),
                    failure_reason=error,
                    sent_at=datetime.now(timezone.utc) if status == "sent" else None,
                )
                session.add(email)
                await session.flush()
        except Exception as e:
            logger.warning("email_tracking_failed", error=str(e))


class MailhogProvider(EmailProvider):
    """ZERO-COST: Local Mailhog SMTP delivery with tracking."""

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: str = "",
        tenant_id: str = "",
        prospect_id: str = "",
    ) -> dict[str, Any]:
        from seo_platform.services.email.adapter import email_adapter
        try:
            email_adapter.send_email(to_email, subject, body)
            logger.info("mailhog_email_sent", to=to_email, campaign_id=campaign_id)

            if tenant_id:
                from seo_platform.services.email_provider import SendGridProvider
                provider = SendGridProvider()
                await provider._track_email(
                    tenant_id, campaign_id, prospect_id, to_email, subject, body, "sent"
                )

            return {"success": True, "provider": "mailhog", "status": "sent"}
        except Exception as e:
            logger.error("mailhog_send_failed", to=to_email, error=str(e))
            return {"success": False, "error": str(e), "status": "failed"}


def get_email_provider() -> EmailProvider:
    """Factory to inject the correct email provider."""
    settings = get_settings()
    if settings.use_mock_providers:
        return MailhogProvider()

    return SendGridProvider()


email_provider = get_email_provider()
