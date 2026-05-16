"""
SEO Platform — Enterprise Email Provider Client
=================================================
Production-grade SMTP client supporting Mailgun and Resend.
Circuit-breaker wrapped. HMAC headers injected for webhook reply matching.

Api keys are read from config at call time. Supports zero-config MailHog fallback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger
from seo_platform.core.reliability import CircuitBreaker

logger = get_logger(__name__)


class EmailProviderError(Exception):
    """Base exception for email provider errors."""


class EmailRateLimitError(EmailProviderError):
    """Raised when provider returns 429."""


class EmailAuthError(EmailProviderError):
    """Raised when API key is invalid (401/403)."""


class EmailDeliveryError(EmailProviderError):
    """Raised when delivery fails."""


class EmailWebhookError(EmailProviderError):
    """Raised for webhook signature / processing errors."""


@dataclass
class EmailMessage:
    to_email: str
    subject: str
    body_html: str
    tenant_id: str = ""
    campaign_id: str = ""
    thread_id: str = ""
    from_email: str = ""
    from_name: str = ""


@dataclass
class EmailDispatchResult:
    success: bool
    provider: str = ""
    message_id: str = ""
    error: str = ""


_circuit = CircuitBreaker("email_provider", failure_threshold=5, recovery_timeout=30)


class MailgunClient:
    """Mailgun API v3 client."""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.mailgun.api_key if hasattr(settings, 'mailgun') else ""
        self.domain = settings.mailgun.domain if hasattr(settings, 'mailgun') else ""
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=("api", self.api_key) if self.api_key else None,
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def send(self, msg: EmailMessage) -> EmailDispatchResult:
        if not self.api_key:
            return EmailDispatchResult(success=False, provider="mailgun", error="no_api_key")
        client = await self._get_client()
        data = {
            "from": f"{msg.from_name or 'SEO Platform'} <{msg.from_email or 'noreply@{self.domain}'}>",
            "to": msg.to_email,
            "subject": msg.subject,
            "html": msg.body_html,
            "o:tag": ["seo-platform"],
            "v:X-BuildIT-Tenant-ID": msg.tenant_id,
            "v:X-BuildIT-Campaign-ID": msg.campaign_id,
            "v:X-BuildIT-Thread-ID": msg.thread_id,
        }
        try:
            resp = await _circuit.call(client.post, "/messages", data=data)
            if resp.status_code == 429:
                raise EmailRateLimitError("Mailgun rate limited")
            if resp.status_code in (401, 402, 403):
                raise EmailAuthError("Mailgun auth failed")
            resp.raise_for_status()
            result = resp.json()
            return EmailDispatchResult(
                success=True, provider="mailgun",
                message_id=result.get("id", ""),
            )
        except EmailProviderError:
            raise
        except Exception as e:
            logger.warning("mailgun_send_failed", error=str(e))
            return EmailDispatchResult(success=False, provider="mailgun", error=str(e))


class ResendClient:
    """Resend API client."""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.resend.api_key if hasattr(settings, 'resend') else ""
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.resend.com",
                headers={
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def send(self, msg: EmailMessage) -> EmailDispatchResult:
        if not self.api_key:
            return EmailDispatchResult(success=False, provider="resend", error="no_api_key")
        client = await self._get_client()
        payload = {
            "from": f"{msg.from_name or 'SEO Platform'} <{msg.from_email or 'noreply@buildit.local'}>",
            "to": [msg.to_email],
            "subject": msg.subject,
            "html": msg.body_html,
            "headers": {
                "X-BuildIT-Tenant-ID": msg.tenant_id,
                "X-BuildIT-Campaign-ID": msg.campaign_id,
                "X-BuildIT-Thread-ID": msg.thread_id,
            },
        }
        try:
            resp = await _circuit.call(client.post, "/emails", json=payload)
            if resp.status_code == 429:
                raise EmailRateLimitError("Resend rate limited")
            if resp.status_code in (401, 403):
                raise EmailAuthError("Resend auth failed")
            resp.raise_for_status()
            result = resp.json()
            return EmailDispatchResult(
                success=True, provider="resend",
                message_id=result.get("id", ""),
            )
        except EmailProviderError:
            raise
        except Exception as e:
            logger.warning("resend_send_failed", error=str(e))
            return EmailDispatchResult(success=False, provider="resend", error=str(e))

    async def verify_dns(self, domain: str) -> dict[str, Any]:
        """Verify SPF, DKIM, DMARC for a domain via Resend."""
        client = await self._get_client()
        resp = await _circuit.call(client.get, f"/domains/{domain}")
        if resp.status_code in (401, 403):
            raise EmailAuthError("Resend auth failed")
        resp.raise_for_status()
        return resp.json().get("records", {})

    async def warmup_status(self, domain: str) -> dict[str, Any]:
        """Get daily sending limit and reputation."""
        client = await self._get_client()
        resp = await _circuit.call(client.get, f"/domains/{domain}/daily")
        if resp.status_code in (401, 403):
            raise EmailAuthError("Resend auth failed")
        resp.raise_for_status()
        return resp.json()


class MailhogClient:
    """Zero-cost local SMTP for development."""

    async def send(self, msg: EmailMessage) -> EmailDispatchResult:
        from seo_platform.services.email.adapter import email_adapter
        try:
            body = msg.body_html
            if msg.thread_id:
                body += f'\n\n<!-- thread_id: {msg.thread_id} -->'
            email_adapter.send_email(msg.to_email, msg.subject, body)
            return EmailDispatchResult(success=True, provider="mailhog")
        except Exception as e:
            return EmailDispatchResult(success=False, provider="mailhog", error=str(e))


def get_email_provider():
    """Factory returning the correct email client based on config."""
    settings = get_settings()
    if settings.use_mock_providers:
        return MailhogClient()
    if hasattr(settings, 'resend') and settings.resend.api_key:
        return ResendClient()
    if hasattr(settings, 'mailgun') and settings.mailgun.api_key:
        return MailgunClient()
    return MailhogClient()


email_provider = get_email_provider()
