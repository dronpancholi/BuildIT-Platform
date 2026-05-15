"""
SEO Platform — Audit Logging System
======================================
Append-only, immutable audit trail for compliance and traceability.

Design principles:
- Every significant action is recorded with full context
- Actor identity (user/system/agent) is always tracked
- Before/after state capture for mutations
- Audit records are immutable (enforced at DB level via trigger)
- Async emission: audit logging never blocks business logic
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.models.tenant import AuditLog

logger = get_logger(__name__)


class AuditEntry(BaseModel):
    """Structured audit log entry for emission."""

    tenant_id: UUID
    event_type: str
    entity_type: str
    entity_id: UUID
    actor_type: str  # "user" | "system" | "agent"
    actor_id: str
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditService:
    """
    Audit logging service.

    Provides both synchronous (await) and fire-and-forget (background task)
    audit emission. The fire-and-forget mode is used in hot paths where
    audit logging must not add latency.

    Usage:
        audit = AuditService()

        # Blocking (for critical operations where audit MUST succeed)
        await audit.record(AuditEntry(
            tenant_id=tenant_id,
            event_type="campaign.launched",
            entity_type="BacklinkCampaign",
            entity_id=campaign_id,
            actor_type="user",
            actor_id=str(user_id),
            after_state={"status": "active"},
        ))

        # Fire-and-forget (for high-volume operations)
        audit.record_async(AuditEntry(...))
    """

    async def record(self, entry: AuditEntry) -> None:
        """
        Record an audit entry. Awaits database write.

        Use for critical operations where audit trail is mandatory.
        """
        try:
            async with get_session() as session:
                audit_log = AuditLog(
                    tenant_id=entry.tenant_id,
                    event_type=entry.event_type,
                    entity_type=entry.entity_type,
                    entity_id=entry.entity_id,
                    actor_type=entry.actor_type,
                    actor_id=entry.actor_id,
                    before_state=entry.before_state,
                    after_state=entry.after_state,
                    metadata_=entry.metadata,
                )
                session.add(audit_log)
            logger.debug(
                "audit_recorded",
                event_type=entry.event_type,
                entity_type=entry.entity_type,
                entity_id=str(entry.entity_id),
            )
        except Exception as e:
            # Audit failures are logged but never propagated — they must not
            # break business logic. Separate monitoring alerts on audit failures.
            logger.error(
                "audit_record_failed",
                event_type=entry.event_type,
                entity_type=entry.entity_type,
                error=str(e),
            )

    def record_async(self, entry: AuditEntry) -> None:
        """
        Record an audit entry as a background task (fire-and-forget).

        Use for high-volume operations where audit latency is unacceptable.
        """
        asyncio.create_task(self.record(entry))

    async def record_state_change(
        self,
        *,
        tenant_id: UUID,
        event_type: str,
        entity_type: str,
        entity_id: UUID,
        actor_type: str,
        actor_id: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        **extra_metadata: Any,
    ) -> None:
        """Convenience method for recording entity state transitions."""
        await self.record(AuditEntry(
            tenant_id=tenant_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_type=actor_type,
            actor_id=actor_id,
            before_state=before,
            after_state=after,
            metadata=extra_metadata,
        ))


# Module-level singleton
audit_service = AuditService()
