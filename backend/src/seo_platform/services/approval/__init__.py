"""
SEO Platform — Approval Service
==================================
Human-in-the-loop supervision system.

This service owns:
- Approval request lifecycle (pending → approved/rejected/expired)
- SLA-based escalation policies
- Decision audit trail
- Temporal Signal integration for workflow resumption
- Approval queue priority management
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from seo_platform.core.audit import AuditEntry, audit_service
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATION_REQUESTED = "modification_requested"
    EXPIRED = "expired"
    DELEGATED = "delegated"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_SLA_HOURS: dict[RiskLevel, int] = {
    RiskLevel.LOW: 24,
    RiskLevel.MEDIUM: 8,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 1,
}


class ApprovalRequest(BaseModel):
    """Human approval request with full context for decision-making."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    workflow_run_id: str
    risk_level: RiskLevel
    category: str  # outreach_templates, keyword_clusters, campaign_launch
    summary: str
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    ai_risk_summary: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    sla_deadline: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def compute_sla_deadline(self) -> datetime:
        hours = RISK_SLA_HOURS.get(self.risk_level, 24)
        return self.created_at + timedelta(hours=hours)


class ApprovalDecision(BaseModel):
    """Decision made by a human reviewer."""
    request_id: UUID
    decision: ApprovalStatus
    decided_by: str  # user_id
    reason: str = ""
    modifications: dict[str, Any] = Field(default_factory=dict)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalService:
    """
    Human supervision service.

    This is the most critical operational surface in the platform.
    Every high-risk operation requires human approval before execution.
    """

    async def create_request(self, request: ApprovalRequest) -> ApprovalRequest:
        """Create a new approval request, persist to DB, and notify reviewers."""
        request.sla_deadline = request.compute_sla_deadline()
        logger.info(
            "approval_request_created",
            request_id=str(request.id),
            risk_level=request.risk_level.value,
            category=request.category,
            sla_deadline=request.sla_deadline.isoformat(),
            tenant_id=str(request.tenant_id),
        )

        # Persist to PostgreSQL
        try:
            from uuid import UUID as PyUUID

            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.approval import (
                ApprovalCategory,
                ApprovalRequestModel,
                ApprovalStatusEnum,
                RiskLevelEnum,
            )

            async with get_tenant_session(request.tenant_id) as session:
                db_model = ApprovalRequestModel(
                    id=PyUUID(str(request.id)),
                    tenant_id=request.tenant_id,
                    workflow_run_id=request.workflow_run_id,
                    category=ApprovalCategory(request.category) if request.category in [e.value for e in ApprovalCategory] else ApprovalCategory.CAMPAIGN_LAUNCH,
                    risk_level=RiskLevelEnum(request.risk_level.value),
                    status=ApprovalStatusEnum.PENDING,
                    summary=request.summary,
                    ai_risk_summary=request.ai_risk_summary,
                    context_snapshot=request.context_snapshot,
                    sla_deadline=request.sla_deadline,
                )
                session.add(db_model)
                await session.flush()
        except Exception as e:
            logger.warning("approval_persistence_failed", error=str(e))

        await audit_service.record(AuditEntry(
            tenant_id=request.tenant_id,
            event_type="approval.request_created",
            entity_type="ApprovalRequest",
            entity_id=request.id,
            actor_type="system",
            actor_id="approval-service",
            after_state=request.model_dump(mode="json"),
        ))

        try:
            from uuid import UUID

            from seo_platform.core.events import ApprovalRequestCreatedEvent, DomainEvent
            from seo_platform.main import get_event_publisher

            publisher = await get_event_publisher()
            if publisher._producer:
                event = ApprovalRequestCreatedEvent(
                    tenant_id=request.tenant_id,
                    correlation_id=request.workflow_run_id,
                    payload={
                        "request_id": str(request.id),
                        "risk_level": request.risk_level.value,
                        "category": request.category,
                        "summary": request.summary,
                        "sla_deadline": request.sla_deadline.isoformat() if request.sla_deadline else "",
                    },
                )
                await publisher.publish(event)
        except Exception as e:
            logger.warning("approval_event_emit_failed", error=str(e))

        try:
            from seo_platform.api.endpoints.realtime.sse import emit_approval_event
            await emit_approval_event(request.tenant_id, str(request.id), "pending")
        except Exception as e:
            logger.warning("sse_approval_event_failed", error=str(e))

        return request

    async def decide(self, decision: ApprovalDecision, workflow_run_id: str, tenant_id: UUID) -> None:
        """Record a human decision, persist to DB, and signal the waiting workflow."""
        logger.info(
            "approval_decision_made",
            request_id=str(decision.request_id),
            decision=decision.decision,
            decided_by=decision.decided_by,
            workflow_run_id=workflow_run_id,
        )

        # Persist decision to PostgreSQL
        try:
            from seo_platform.core.database import get_tenant_session
            from seo_platform.models.approval import ApprovalRequestModel, ApprovalStatusEnum

            async with get_tenant_session(tenant_id) as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(ApprovalRequestModel).where(ApprovalRequestModel.id == decision.request_id)
                )
                db_record = result.scalar_one_or_none()
                if db_record:
                    db_record.status = ApprovalStatusEnum(decision.decision.value)
                    db_record.decided_at = decision.decided_at
                    db_record.decision_reason = decision.reason
                    db_record.modifications = decision.modifications
                    if decision.decided_by:
                        try:
                            from uuid import UUID as PyUUID
                            db_record.decided_by = PyUUID(decision.decided_by)
                        except ValueError:
                            db_record.decided_by = None
                    await session.flush()
        except Exception as e:
            logger.warning("approval_decision_persistence_failed", error=str(e))

        try:
            from seo_platform.core.temporal_client import get_temporal_client
            client = await get_temporal_client()

            handle = client.get_workflow_handle(workflow_run_id)
            await handle.signal(
                "approval_decision",
                decision.model_dump_json(),
            )
            logger.info(
                "workflow_signaled",
                workflow_run_id=workflow_run_id,
                signal="approval_decision",
            )
        except Exception as e:
            logger.error(
                "workflow_signal_failed",
                workflow_run_id=workflow_run_id,
                error=str(e),
            )

        try:
            from seo_platform.core.events import ApprovalDecidedEvent
            from seo_platform.main import get_event_publisher

            publisher = await get_event_publisher()
            if publisher._producer:
                event = ApprovalDecidedEvent(
                    tenant_id=tenant_id,
                    correlation_id=workflow_run_id,
                    payload={
                        "request_id": str(decision.request_id),
                        "decision": decision.decision,
                        "decided_by": decision.decided_by,
                        "reason": decision.reason,
                    },
                )
                await publisher.publish(event)
        except Exception as e:
            logger.warning("approval_decision_event_failed", error=str(e))

        try:
            from seo_platform.api.endpoints.realtime.sse import emit_approval_event
            await emit_approval_event(tenant_id, str(decision.request_id), decision.decision)
        except Exception as e:
            logger.warning("sse_approval_decision_event_failed", error=str(e))


approval_service = ApprovalService()
