"""
SEO Platform — Email Webhook Listener
=======================================
FastAPI router for inbound email webhooks from Mailgun and Resend.
HMAC signature verification enforced. Events forwarded to webhook handler.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger
from seo_platform.services.email.webhook_handler import process_webhook_event

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/email", tags=["Webhooks"])


def _verify_mailgun_signature(
    timestamp: str, token: str, signature: str,
) -> bool:
    """Verify Mailgun webhook HMAC signature."""
    signing_key = getattr(get_settings(), "email_webhook_signing_key", "") or \
                  getattr(get_settings(), "mailgun_webhook_key", "")
    if not signing_key:
        logger.warning("mailgun_webhook_key_not_configured")
        return False
    msg = f"{timestamp}{token}".encode()
    expected = hmac.new(
        key=signing_key.encode(),
        msg=msg,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_resend_signature(request: Request, payload_body: bytes) -> bool:
    """Verify Resend webhook via Svix-Signature header."""
    signing_key = getattr(get_settings(), "email_webhook_signing_key", "") or \
                  getattr(get_settings(), "resend_webhook_key", "")
    if not signing_key:
        logger.warning("resend_webhook_key_not_configured")
        return False
    svix_signature = request.headers.get("svix-signature", "")
    if not svix_signature:
        return False
    expected = hmac.new(
        key=signing_key.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    parts = svix_signature.split(",")
    for part in parts:
        if part.startswith("v1,"):
            received = part[3:]
            if hmac.compare_digest(expected, received):
                return True
    return False


@router.post("/mailgun")
async def mailgun_webhook(request: Request) -> dict[str, Any]:
    """
    Receive Mailgun webhook events.
    Verifies timestamp+token+signature before processing.
    """
    try:
        payload: dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    signature_data = payload.get("signature", {})
    timestamp = signature_data.get("timestamp", "")
    token = signature_data.get("token", "")
    signature = signature_data.get("signature", "")

    if not _verify_mailgun_signature(timestamp, token, signature):
        logger.warning("mailgun_webhook_invalid_signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    logger.info("mailgun_webhook_validated", event=payload.get("event-data", {}).get("event"))
    result = await process_webhook_event(payload, "mailgun")
    return result


@router.post("/resend")
async def resend_webhook(request: Request) -> dict[str, Any]:
    """
    Receive Resend webhook events.
    Verifies Svix-Signature header before processing.
    """
    body = await request.body()
    payload: dict = await request.json()

    if not _verify_resend_signature(request, body):
        logger.warning("resend_webhook_invalid_signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    logger.info("resend_webhook_validated", event=payload.get("type"))
    result = await process_webhook_event(payload, "resend")
    return result


@router.post("/generic")
async def generic_webhook(request: Request) -> dict[str, Any]:
    """
    Generic webhook endpoint for testing or custom providers.
    No signature verification (development only).
    """
    settings = get_settings()
    if settings.is_production:
        raise HTTPException(status_code=403, detail="Generic webhooks disabled in production")
    payload: dict = await request.json()
    logger.info("generic_webhook_received", provider=payload.get("provider", "unknown"))
    result = await process_webhook_event(payload, payload.get("provider", "generic"))
    return result


@router.get("/health")
async def webhook_health() -> dict[str, Any]:
    """Health check for webhook listener."""
    signing_key = getattr(get_settings(), "email_webhook_signing_key", "")
    return {
        "status": "healthy",
        "webhook_key_configured": bool(signing_key),
    }
