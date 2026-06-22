"""
SEO Platform — Webhook Event Handler
======================================
Processes incoming email webhook events (delivered, bounced, opened, replied).
Publishes domain events to Kafka and signals Temporal child workflows on reply.

Idempotency: every event is deduped via
``core.webhook_dedup.check_and_record_webhook_event`` keyed on
``(provider, event_id)``. Provider retries that resend the same event_id
are silently skipped, so downstream effects (Kafka emit, Temporal
signal, status update) cannot fire twice.
"""

from __future__ import annotations

import json
from typing import Any

from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import (
    seo_webhook_events_total,
    seo_webhook_duplicates_total,
)
from seo_platform.core.webhook_dedup import check_and_record_webhook_event

logger = get_logger(__name__)


async def _get_temporal_client():
    """Lazy import to avoid circular dependency at module load."""
    from seo_platform.core.temporal_client import get_temporal_client
    return await get_temporal_client()


def _emit_kafka_event(topic: str, tenant_id: str, payload: dict) -> None:
    """Publish a domain event to Kafka. Best-effort, non-blocking."""
    try:
        from seo_platform.core.events import kafka_producer
        kafka_producer.emit(topic, tenant_id, payload)
    except Exception as e:
        logger.warning("kafka_emit_failed", topic=topic, error=str(e))


def _extract_event_id(payload: dict, provider: str) -> str:
    """Pull a stable per-provider event id from the payload.

    Returns an empty string if no id is present, in which case the
    caller will treat the event as non-idempotent and let it through.
    """
    if provider == "mailgun":
        event_data = payload.get("event-data") or {}
        return (
            event_data.get("id")
            or event_data.get("message", {}).get("headers", {}).get("message-id")
            or ""
        )
    if provider == "resend":
        return payload.get("id") or payload.get("svix-id") or ""
    return payload.get("event_id") or payload.get("id") or ""


async def process_webhook_event(payload: dict, provider: str) -> dict[str, Any]:
    """
    Process an incoming email webhook event.

    Supported event types: delivered, bounced, opened, replied.
    On 'replied', signals the corresponding OutreachThreadWorkflow child.

    Idempotency: a unique (provider, event_id) constraint ensures that
    provider retries of the same event are skipped. The same event id
    arriving via the format-agnostic /webhooks/inbound/email surface
    is deduped separately by AuditLog.metadata_.message_id.
    """
    event_type = _detect_event_type(payload, provider)
    metadata = _extract_metadata(payload, provider)

    tenant_id = metadata.get("tenant_id", "")
    campaign_id = metadata.get("campaign_id", "")
    prospect_domain = metadata.get("prospect_domain", "")
    thread_id = metadata.get("thread_id", "")

    event_id = _extract_event_id(payload, provider)
    proceed = await check_and_record_webhook_event(
        provider=provider,
        event_id=event_id,
        tenant_id=tenant_id or None,
        thread_id=thread_id or None,
        event_type=event_type,
    )
    if not proceed:
        seo_webhook_duplicates_total.labels(provider=provider).inc()
        seo_webhook_events_total.labels(
            provider=provider, event_type=event_type or "unknown", outcome="duplicate",
        ).inc()
        return {
            "status": "duplicate",
            "provider": provider,
            "event_type": event_type,
            "thread_id": thread_id,
        }

    logger.info(
        "webhook_event_received",
        provider=provider,
        event_type=event_type,
        thread_id=thread_id,
        campaign_id=campaign_id,
    )

    _emit_kafka_event(f"email.{event_type}", tenant_id, {
        "provider": provider,
        "event_type": event_type,
        "tenant_id": tenant_id,
        "campaign_id": campaign_id,
        "prospect_domain": prospect_domain,
        "thread_id": thread_id,
        "payload": payload,
    })

    if event_type == "replied" and thread_id:
        try:
            temporal = await _get_temporal_client()
            handle = temporal.get_workflow_handle(thread_id)
            reply_data = json.dumps({
                "thread_id": thread_id,
                "prospect_domain": prospect_domain,
                "campaign_id": campaign_id,
                "from_email": metadata.get("from_email", ""),
                "subject": metadata.get("subject", ""),
                "body_preview": metadata.get("body_preview", "")[:500],
                "event_type": "replied",
            })
            await handle.signal("reply_received", reply_data)
            logger.info("temporal_signal_sent", thread_id=thread_id, signal="reply_received")
        except Exception as e:
            logger.warning("temporal_signal_failed", thread_id=thread_id, error=str(e))

    seo_webhook_events_total.labels(
        provider=provider, event_type=event_type or "unknown", outcome="accepted",
    ).inc()

    return {
        "status": "accepted",
        "event_type": event_type,
        "thread_id": thread_id,
    }


def _detect_event_type(payload: dict, provider: str) -> str:
    """Detect the event type from provider-specific payload format."""
    if provider == "mailgun":
        event = payload.get("event-data", {}).get("event", "")
        if event == "delivered":
            return "delivered"
        if event == "bounced":
            return "bounced"
        if event == "opened":
            return "opened"
        if event in ("complained", "unsubscribed"):
            return event
        if event == "stored":
            return "delivered"
        return event

    if provider == "resend":
        event_type = payload.get("type", "")
        if event_type == "email.delivered":
            return "delivered"
        if event_type == "email.bounced":
            return "bounced"
        if event_type == "email.opened":
            return "opened"
        if event_type == "email.complained":
            return "complained"
        return event_type

    return payload.get("event", "unknown")


def _extract_metadata(payload: dict, provider: str) -> dict[str, str]:
    """Extract BuildIT metadata headers from provider-specific payload."""
    metadata: dict[str, str] = {}

    if provider == "mailgun":
        event_data = payload.get("event-data", {})
        message = event_data.get("message", {})
        headers = message.get("headers", {})
        user_vars = message.get("user-variables", {})

        metadata["tenant_id"] = (
            user_vars.get("X-BuildIT-Tenant-ID", "") or
            headers.get("X-BuildIT-Tenant-ID", "")
        )
        metadata["campaign_id"] = (
            user_vars.get("X-BuildIT-Campaign-ID", "") or
            headers.get("X-BuildIT-Campaign-ID", "")
        )
        metadata["thread_id"] = (
            user_vars.get("X-BuildIT-Thread-ID", "") or
            headers.get("X-BuildIT-Thread-ID", "")
        )
        metadata["prospect_domain"] = metadata["thread_id"].replace("outreach_", "").split("_", 1)[-1] if metadata["thread_id"] else ""
        metadata["from_email"] = headers.get("from", "")
        metadata["subject"] = headers.get("subject", "")

    elif provider == "resend":
        headers = payload.get("headers", {}) or {}
        metadata["tenant_id"] = headers.get("X-BuildIT-Tenant-ID", "")
        metadata["campaign_id"] = headers.get("X-BuildIT-Campaign-ID", "")
        metadata["thread_id"] = headers.get("X-BuildIT-Thread-ID", "")
        metadata["prospect_domain"] = metadata["thread_id"].replace("outreach_", "").split("_", 1)[-1] if metadata["thread_id"] else ""
        metadata["from_email"] = headers.get("from", "")
        metadata["subject"] = headers.get("subject", "")

    else:
        metadata = {
            "tenant_id": payload.get("tenant_id", ""),
            "campaign_id": payload.get("campaign_id", ""),
            "thread_id": payload.get("thread_id", ""),
            "prospect_domain": payload.get("prospect_domain", ""),
        }

    return metadata
