"""
SEO Platform — Webhook Idempotency
====================================

Provides a single ``check_and_record_webhook_event`` helper that all
webhook surfaces call at the top of their handlers. Returns ``True``
if this is a new event (proceed to process); returns ``False`` if the
event has already been processed (skip silently, return 200).

The helper relies on the unique constraint
``uq_processed_webhook_events_provider_event`` (provider, event_id)
to make concurrent retries safe. On a duplicate insert, the function
returns ``False`` without raising.

If ``event_id`` is empty or missing, the helper returns ``True``
(allow the request through) and logs a warning. Webhooks without
provider-supplied event IDs cannot be idempotent, so the caller is
expected to fall back to its own dedup mechanism (e.g. the
``AuditLog.metadata_.message_id`` lookup in ``inbound_webhooks.py``).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


async def check_and_record_webhook_event(
    provider: str,
    event_id: str,
    tenant_id: str | UUID | None = None,
    thread_id: str | None = None,
    event_type: str | None = None,
) -> bool:
    """
    Atomically check whether ``(provider, event_id)`` has been processed
    before, and if not, record it. Returns ``True`` if the caller should
    proceed, ``False`` if the event is a duplicate.

    The insert is the dedup mechanism. A concurrent duplicate will fail
    the unique constraint, which we catch and treat as "already
    processed". No advisory locks or SELECT-then-INSERT races.
    """
    if not provider or not event_id:
        logger.warning(
            "webhook_dedup_skipped_missing_ids",
            provider=provider,
            event_id_present=bool(event_id),
        )
        return True

    tenant_uuid: UUID | None = None
    if tenant_id:
        try:
            tenant_uuid = UUID(str(tenant_id))
        except (TypeError, ValueError):
            tenant_uuid = None

    try:
        async with get_session() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO processed_webhook_events
                        (provider, event_id, tenant_id, thread_id, event_type)
                    VALUES
                        (:provider, :event_id, :tenant_id, :thread_id, :event_type)
                    ON CONFLICT (provider, event_id) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "provider": provider[:50],
                    "event_id": event_id[:500],
                    "tenant_id": tenant_uuid,
                    "thread_id": (thread_id or "")[:255],
                    "event_type": (event_type or "")[:50],
                },
            )
            inserted = result.scalar_one_or_none() is not None
        if not inserted:
            logger.info(
                "webhook_event_duplicate_skipped",
                provider=provider,
                event_id_prefix=event_id[:80],
            )
        return inserted
    except IntegrityError:
        logger.info(
            "webhook_event_duplicate_skipped",
            provider=provider,
            event_id_prefix=event_id[:80],
        )
        return False
    except Exception as exc:
        # If the table doesn't exist (e.g. migration not applied in
        # some environment), log and allow the request through. We
        # do NOT want to break webhook intake on a missing table.
        logger.warning(
            "webhook_dedup_table_unavailable",
            provider=provider,
            error=str(exc),
        )
        return True


async def is_webhook_event_processed(
    provider: str, event_id: str,
) -> bool:
    """Pure check (no insert). Useful for the format-agnostic surface
    that already writes to ``AuditLog`` and just wants to know whether
    a particular message_id has been seen.
    """
    if not provider or not event_id:
        return False
    try:
        async with get_session() as session:
            row = await session.execute(
                text(
                    """
                    SELECT 1 FROM processed_webhook_events
                    WHERE provider = :provider AND event_id = :event_id
                    LIMIT 1
                    """
                ),
                {"provider": provider[:50], "event_id": event_id[:500]},
            )
            return row.scalar_one_or_none() is not None
    except Exception as exc:
        logger.warning("webhook_dedup_check_failed", provider=provider, error=str(exc))
        return False
