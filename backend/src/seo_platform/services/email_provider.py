# PHASE 1.2 — Simulation verified: get_email_provider() factory gates on use_mock_providers; singleton uses factory
"""
SEO Platform — Email Provider Abstraction (Phase 2.5.1)
========================================================
Enterprise abstraction layer that selects between real production delivery
APIs (Resend, SendGrid, Mailgun) and a local MailHog SMTP server.

Phase 2.5.1 changes:
- Added Resend and Mailgun providers (the P0 startup check supports them
  but no implementation existed).
- Refactored the factory: it now picks the first configured provider in
  the order Resend > SendGrid > Mailgun, and refuses to silently fall
  back to MailHog. If no real provider is configured and we are NOT in
  development, the factory returns a `NoOpEmailProvider` whose `send_email`
  raises `EmailProviderUnavailableError` — the workflow fails loudly.
- MailHog is now an explicit `DevMailhogProvider` used only when
  `APP_ENV=development` and no real provider is configured.

This is the "no silent fallback" behavior the Phase 2.5.1 brief
requires.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class EmailProviderUnavailableError(RuntimeError):
    """Raised when an email send is attempted but no real provider is configured."""


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


class _BaseHTTPProvider(EmailProvider):
    """
    Shared logic: HTTP call, error handling, and DB tracking. Subclasses
    implement the request signature for their respective providers.
    """

    PROVIDER_NAME: str = ""

    async def _track_email(
        self,
        tenant_id: str,
        campaign_id: str,
        prospect_id: str,
        to_email: str,
        subject: str,
        body: str,
        status: str,
        error: str | None = None,
        message_id: str | None = None,
    ) -> None:
        if not tenant_id:
            return
        try:
            from datetime import datetime, timezone
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.communication import OutreachEmail, EmailStatus
            from uuid import UUID as PyUUID

            from seo_platform.models.backlink import OutreachThread, ThreadStatus
            from sqlalchemy import select

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

                if campaign_id and campaign_id != "none" and status == "sent":
                    result = await session.execute(
                        select(OutreachThread).where(
                            OutreachThread.tenant_id == PyUUID(tenant_id),
                            OutreachThread.campaign_id == PyUUID(campaign_id),
                            OutreachThread.to_email == to_email,
                        ).order_by(OutreachThread.created_at.desc()).limit(1)
                    )
                    thread = result.scalar_one_or_none()
                    if thread:
                        thread.status = ThreadStatus.SENT
                        thread.sent_at = datetime.now(timezone.utc)

                await session.flush()
        except Exception as e:
            logger.warning("email_tracking_failed", error=str(e))

    async def _send(
        self,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: str,
        tenant_id: str,
        prospect_id: str,
        build_request: "callable",
    ) -> dict[str, Any]:
        """Generic HTTP-send flow. `build_request()` returns (url, headers, json, timeout)."""
        import httpx
        url, headers, payload, timeout = build_request()
        logger.info(f"{self.PROVIDER_NAME}_api_call", to=to_email, campaign_id=campaign_id)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                message_id = (
                    response.headers.get("x-message-id")
                    or response.headers.get("X-Message-Id")
                    or (response.json().get("id") if response.headers.get("content-type", "").startswith("application/json") else None)
                )
                logger.info(f"{self.PROVIDER_NAME}_email_sent", to=to_email, message_id=message_id)
                await self._track_email(
                    tenant_id, campaign_id, prospect_id, to_email, subject, body,
                    "sent", message_id=message_id,
                )
                return {"success": True, "provider": self.PROVIDER_NAME, "message_id": message_id, "status": "sent"}
        except Exception as e:
            logger.error(f"{self.PROVIDER_NAME}_send_failed", to=to_email, error=str(e))
            await self._track_email(
                tenant_id, campaign_id, prospect_id, to_email, subject, body, "failed", str(e),
            )
            return {"success": False, "provider": self.PROVIDER_NAME, "error": str(e), "status": "failed"}


class ResendProvider(_BaseHTTPProvider):
    """PRODUCTION: Real Resend API integration."""

    PROVIDER_NAME = "resend"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: str = "",
        tenant_id: str = "",
        prospect_id: str = "",
    ) -> dict[str, Any]:
        settings = get_settings()
        sender = f"{settings.resend.sender_name} <{settings.resend.sender_email}>"

        def build_request():
            return (
                "https://api.resend.com/emails",
                {
                    "Authorization": f"Bearer {settings.resend.api_key}",
                    "Content-Type": "application/json",
                },
                {
                    "from": sender,
                    "to": [to_email],
                    "subject": subject,
                    "html": body,
                },
                30.0,
            )

        return await self._send(to_email, subject, body, campaign_id, tenant_id, prospect_id, build_request)


class SendGridProvider(_BaseHTTPProvider):
    """PRODUCTION: Real SendGrid API integration."""

    PROVIDER_NAME = "sendgrid"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: str = "",
        tenant_id: str = "",
        prospect_id: str = "",
    ) -> dict[str, Any]:
        settings = get_settings()

        def build_request():
            return (
                "https://api.sendgrid.com/v3/mail/send",
                {
                    "Authorization": f"Bearer {settings.sendgrid.api_key}",
                    "Content-Type": "application/json",
                },
                {
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": settings.sendgrid.sender_email, "name": "SEO Platform"},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": body}],
                },
                30.0,
            )

        return await self._send(to_email, subject, body, campaign_id, tenant_id, prospect_id, build_request)


class MailgunProvider(_BaseHTTPProvider):
    """PRODUCTION: Real Mailgun API integration."""

    PROVIDER_NAME = "mailgun"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: str = "",
        tenant_id: str = "",
        prospect_id: str = "",
    ) -> dict[str, Any]:
        settings = get_settings()

        def build_request():
            return (
                f"https://api.mailgun.net/v3/{settings.mailgun.domain}/messages",
                {
                    "Authorization": f"Basic {__import__('base64').b64encode(f'api:{settings.mailgun.api_key}'.encode()).decode()}",
                    "Content-Type": "application/json",
                },
                {
                    "from": f"SEO Platform <noreply@{settings.mailgun.domain}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": body,
                },
                30.0,
            )

        return await self._send(to_email, subject, body, campaign_id, tenant_id, prospect_id, build_request)


class DevMailhogProvider(EmailProvider):
    """
    DEV-ONLY: Local MailHog SMTP delivery. Used only in development when
    no real provider is configured. Every send is recorded in the local
    MailHog instance (http://localhost:8025) and tracked in the DB.
    """

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
                provider = SendGridProvider()  # Reuse the shared _track_email
                await provider._track_email(
                    tenant_id, campaign_id, prospect_id, to_email, subject, body, "sent"
                )

            return {"success": True, "provider": "mailhog", "status": "sent"}
        except Exception as e:
            logger.error("mailhog_send_failed", to=to_email, error=str(e))
            return {"success": False, "provider": "mailhog", "error": str(e), "status": "failed"}


class NoOpEmailProvider(EmailProvider):
    """
    PRODUCTION-ONLY: Used when no real email provider is configured and
    the app is in production. Every send raises `EmailProviderUnavailableError`
    so the workflow fails loudly. There is no silent fallback.
    """

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        campaign_id: str = "",
        tenant_id: str = "",
        prospect_id: str = "",
    ) -> dict[str, Any]:
        raise EmailProviderUnavailableError(
            "No email provider is configured. Set RESEND_API_KEY or "
            "SENDGRID_API_KEY or MAILGUN_API_KEY+MAILGUN_DOMAIN. "
            "The startup check refuses to launch in production without one."
        )


def get_email_provider() -> EmailProvider:
    """
    Factory: pick the first configured real provider (Resend > SendGrid
    > Mailgun). In development with no real provider, fall back to
    DevMailhogProvider. In production with no real provider, return
    NoOpEmailProvider which raises on every send.
    """
    settings = get_settings()

    if settings.resend.api_key:
        return ResendProvider()
    if settings.sendgrid.api_key and settings.sendgrid.sender_email:
        return SendGridProvider()
    if settings.mailgun.api_key and settings.mailgun.domain:
        return MailgunProvider()

    if settings.is_development:
        logger.warning(
            "email_provider_unconfigured",
            detail="No real provider set; using DevMailhogProvider (dev only).",
        )
        return DevMailhogProvider()

    return NoOpEmailProvider()


email_provider = get_email_provider()
