"""
SEO Platform — Approval Workflow Engine
========================================
Dashboard, approve/reject/escalate, bulk operations, and analytics
for human-in-the-loop approval management.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case, and_, or_

from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.models.approval import (
    ApprovalRequestModel,
    ApprovalStatusEnum,
    ApprovalCategory,
    RiskLevelEnum,
)
from seo_platform.schemas import APIResponse, ResponseMeta

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _enum_val(val) -> str:
    """Extract .value from an enum, or return the string directly."""
    return val.value if hasattr(val, "value") else str(val)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class ApprovalDetail(BaseModel):
    id: UUID
    workflow_run_id: str
    category: str
    risk_level: str
    status: str
    summary: str
    ai_risk_summary: str
    context_snapshot: dict = Field(default_factory=dict)
    sla_deadline: str | None = None
    escalation_count: int
    assigned_to: str | None = None
    decided_by: str | None = None
    decided_at: str | None = None
    decision_reason: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class AuditEntry(BaseModel):
    action: str
    performed_by: str | None = None
    performed_at: str | None = None
    notes: str = ""


class ApprovalDetailResponse(BaseModel):
    approval: ApprovalDetail
    audit_trail: list[AuditEntry] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    total_pending: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_escalated: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_risk: dict[str, int] = Field(default_factory=dict)
    overdue_count: int = 0
    recent_decisions: list[ApprovalDetail] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    approval_rate: float = 0.0
    rejection_rate: float = 0.0
    average_time_to_decision_hours: float = 0.0
    by_requester: dict[str, int] = Field(default_factory=dict)
    rejection_reasons: list[dict[str, int | str]] = Field(default_factory=list)
    total_decisions: int = 0


class BulkApproveRequest(BaseModel):
    approval_ids: list[UUID] = Field(..., min_length=1)
    notes: str = ""


# ---------------------------------------------------------------------------
# GET /dashboard — Approval dashboard summary
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_model=APIResponse[DashboardResponse])
async def approval_dashboard(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[DashboardResponse]:
    tenant_id = user.tenant_id
    now = datetime.now(UTC)

    async with get_tenant_session(tenant_id) as session:
        # Total by status
        status_counts = await session.execute(
            select(ApprovalRequestModel.status, func.count())
            .where(ApprovalRequestModel.tenant_id == tenant_id)
            .group_by(ApprovalRequestModel.status)
        )
        status_map = {
            _enum_val(row[0]): row[1]
            for row in status_counts.all()
        }

        # Counts by type (category)
        type_counts = await session.execute(
            select(ApprovalRequestModel.category, func.count())
            .where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
            )
            .group_by(ApprovalRequestModel.category)
        )
        by_type = {
            _enum_val(row[0]): row[1]
            for row in type_counts.all()
        }

        # Counts by risk level (pending only)
        risk_counts = await session.execute(
            select(ApprovalRequestModel.risk_level, func.count())
            .where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
            )
            .group_by(ApprovalRequestModel.risk_level)
        )
        by_risk = {
            _enum_val(row[0]): row[1]
            for row in risk_counts.all()
        }

        # Overdue (past SLA deadline)
        overdue_result = await session.execute(
            select(func.count()).select_from(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
                ApprovalRequestModel.sla_deadline.isnot(None),
                ApprovalRequestModel.sla_deadline < now,
            )
        )
        overdue_count = overdue_result.scalar_one()

        # Recent decisions (last 10)
        recent_result = await session.execute(
            select(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status.in_([
                    ApprovalStatusEnum.APPROVED,
                    ApprovalStatusEnum.REJECTED,
                ]),
            )
            .order_by(ApprovalRequestModel.decided_at.desc().nullslast())
            .limit(10)
        )
        recent = [
            _approval_to_detail(a)
            for a in recent_result.scalars().all()
        ]

        return APIResponse(
            data=DashboardResponse(
                total_pending=status_map.get("pending", 0),
                total_approved=status_map.get("approved", 0),
                total_rejected=status_map.get("rejected", 0),
                total_escalated=0,
                by_type=by_type,
                by_risk=by_risk,
                overdue_count=overdue_count,
                recent_decisions=recent,
            )
        )


# ---------------------------------------------------------------------------
# GET /analytics — Approval analytics
# ---------------------------------------------------------------------------
@router.get("/analytics", response_model=APIResponse[AnalyticsResponse])
async def approval_analytics(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[AnalyticsResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        # Total decisions
        total_result = await session.execute(
            select(func.count()).select_from(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status.in_([
                    ApprovalStatusEnum.APPROVED,
                    ApprovalStatusEnum.REJECTED,
                ]),
            )
        )
        total_decisions = total_result.scalar_one()

        # Approved count
        approved_result = await session.execute(
            select(func.count()).select_from(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatusEnum.APPROVED,
            )
        )
        approved_count = approved_result.scalar_one()

        # Rejected count
        rejected_result = await session.execute(
            select(func.count()).select_from(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatusEnum.REJECTED,
            )
        )
        rejected_count = rejected_result.scalar_one()

        approval_rate = (approved_count / total_decisions * 100) if total_decisions > 0 else 0.0
        rejection_rate = (rejected_count / total_decisions * 100) if total_decisions > 0 else 0.0

        # Average time to decision
        avg_result = await session.execute(
            select(
                func.avg(
                    func.extract("epoch", ApprovalRequestModel.decided_at - ApprovalRequestModel.created_at) / 3600.0
                )
            ).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.decided_at.isnot(None),
                ApprovalRequestModel.created_at.isnot(None),
            )
        )
        avg_hours = avg_result.scalar_one() or 0.0

        # Rejection reasons
        rejection_reasons_result = await session.execute(
            select(ApprovalRequestModel.decision_reason, func.count())
            .where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatusEnum.REJECTED,
                ApprovalRequestModel.decision_reason != "",
            )
            .group_by(ApprovalRequestModel.decision_reason)
            .order_by(func.count().desc())
            .limit(10)
        )
        rejection_reasons = [
            {"reason": row[0], "count": row[1]}
            for row in rejection_reasons_result.all()
        ]

        return APIResponse(
            data=AnalyticsResponse(
                approval_rate=round(approval_rate, 1),
                rejection_rate=round(rejection_rate, 1),
                average_time_to_decision_hours=round(float(avg_hours), 1),
                by_requester={},
                rejection_reasons=rejection_reasons,
                total_decisions=total_decisions,
            )
        )


# ---------------------------------------------------------------------------
# GET /{approval_id} — Full approval detail
# ---------------------------------------------------------------------------
@router.get("/{approval_id}", response_model=APIResponse[ApprovalDetailResponse])
async def get_approval_detail(
    approval_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ApprovalDetailResponse]:
    tenant_id = user.tenant_id

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(ApprovalRequestModel).where(
                ApprovalRequestModel.id == approval_id,
                ApprovalRequestModel.tenant_id == tenant_id,
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")

        detail = _approval_to_detail(approval)

        # Build audit trail
        audit_trail = _build_audit_trail(approval)

        # Available actions based on current status
        available_actions = []
        if approval.status == ApprovalStatusEnum.PENDING:
            available_actions = ["approve", "reject", "escalate"]
        elif approval.status == ApprovalStatusEnum.APPROVED:
            available_actions = []
        elif approval.status == ApprovalStatusEnum.REJECTED:
            available_actions = []
        else:
            available_actions = ["approve", "reject", "escalate"]

        return APIResponse(
            data=ApprovalDetailResponse(
                approval=detail,
                audit_trail=audit_trail,
                available_actions=available_actions,
            )
        )


# ---------------------------------------------------------------------------
# POST /{approval_id}/approve — Approve with optional notes
# ---------------------------------------------------------------------------
class ApproveRequest(BaseModel):
    notes: str = ""


@router.post("/{approval_id}/approve", response_model=APIResponse[ApprovalDetail])
async def approve_request(
    approval_id: UUID,
    body: ApproveRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ApprovalDetail]:
    tenant_id = user.tenant_id
    now = datetime.now(UTC)

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(ApprovalRequestModel).where(
                ApprovalRequestModel.id == approval_id,
                ApprovalRequestModel.tenant_id == tenant_id,
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if approval.status != ApprovalStatusEnum.PENDING:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot approve: current status is '{_enum_val(approval.status)}'",
            )

        approval.status = ApprovalStatusEnum.APPROVED
        approval.decided_by = user.id
        approval.decided_at = now
        approval.decision_reason = body.notes

        await session.flush()
        await session.refresh(approval)

        logger.info(
            "approval_approved",
            tenant_id=str(tenant_id),
            approval_id=str(approval_id),
            decided_by=str(user.id),
        )

        return APIResponse(data=_approval_to_detail(approval))


# ---------------------------------------------------------------------------
# POST /{approval_id}/reject — Reject with required reason
# ---------------------------------------------------------------------------
class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Rejection reason is required")


@router.post("/{approval_id}/reject", response_model=APIResponse[ApprovalDetail])
async def reject_request(
    approval_id: UUID,
    body: RejectRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ApprovalDetail]:
    tenant_id = user.tenant_id
    now = datetime.now(UTC)

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(ApprovalRequestModel).where(
                ApprovalRequestModel.id == approval_id,
                ApprovalRequestModel.tenant_id == tenant_id,
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if approval.status != ApprovalStatusEnum.PENDING:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot reject: current status is '{_enum_val(approval.status)}'",
            )

        approval.status = ApprovalStatusEnum.REJECTED
        approval.decided_by = user.id
        approval.decided_at = now
        approval.decision_reason = body.reason

        await session.flush()
        await session.refresh(approval)

        logger.info(
            "approval_rejected",
            tenant_id=str(tenant_id),
            approval_id=str(approval_id),
            decided_by=str(user.id),
            reason=body.reason,
        )

        return APIResponse(data=_approval_to_detail(approval))


# ---------------------------------------------------------------------------
# POST /{approval_id}/escalate — Escalate to higher authority
# ---------------------------------------------------------------------------
class EscalateRequest(BaseModel):
    reason: str = Field(..., min_length=1)


@router.post("/{approval_id}/escalate", response_model=APIResponse[ApprovalDetail])
async def escalate_request(
    approval_id: UUID,
    body: EscalateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ApprovalDetail]:
    tenant_id = user.tenant_id
    now = datetime.now(UTC)

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(ApprovalRequestModel).where(
                ApprovalRequestModel.id == approval_id,
                ApprovalRequestModel.tenant_id == tenant_id,
            )
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if approval.status != ApprovalStatusEnum.PENDING:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot escalate: current status is '{_enum_val(approval.status)}'",
            )

        approval.escalation_count = (approval.escalation_count or 0) + 1
        approval.updated_at = now

        await session.flush()
        await session.refresh(approval)

        logger.info(
            "approval_escalated",
            tenant_id=str(tenant_id),
            approval_id=str(approval_id),
            escalation_count=approval.escalation_count,
            reason=body.reason,
        )

        return APIResponse(data=_approval_to_detail(approval))


# ---------------------------------------------------------------------------
# POST /bulk-approve — Approve multiple approvals at once
# ---------------------------------------------------------------------------
@router.post("/bulk-approve", response_model=APIResponse[list[ApprovalDetail]])
async def bulk_approve(
    body: BulkApproveRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[ApprovalDetail]]:
    tenant_id = user.tenant_id
    now = datetime.now(UTC)
    approved: list[ApprovalDetail] = []

    async with get_tenant_session(tenant_id) as session:
        for aid in body.approval_ids:
            result = await session.execute(
                select(ApprovalRequestModel).where(
                    ApprovalRequestModel.id == aid,
                    ApprovalRequestModel.tenant_id == tenant_id,
                )
            )
            approval = result.scalar_one_or_none()
            if not approval:
                logger.warning("bulk_approve_skip_not_found", approval_id=str(aid))
                continue

            if approval.status != ApprovalStatusEnum.PENDING:
                logger.warning(
                    "bulk_approve_skip_status",
                    approval_id=str(aid),
                    status=_enum_val(approval.status),
                )
                continue

            approval.status = ApprovalStatusEnum.APPROVED
            approval.decided_by = user.id
            approval.decided_at = now
            approval.decision_reason = body.notes or "Bulk approved"
            await session.flush()
            await session.refresh(approval)
            approved.append(_approval_to_detail(approval))

        logger.info(
            "bulk_approve_completed",
            tenant_id=str(tenant_id),
            requested=len(body.approval_ids),
            approved=len(approved),
        )

        return APIResponse(data=approved)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _approval_to_detail(a: ApprovalRequestModel) -> ApprovalDetail:
    return ApprovalDetail(
        id=a.id,
        workflow_run_id=a.workflow_run_id,
        category=_enum_val(a.category),
        risk_level=_enum_val(a.risk_level),
        status=_enum_val(a.status),
        summary=a.summary,
        ai_risk_summary=a.ai_risk_summary,
        context_snapshot=a.context_snapshot or {},
        sla_deadline=a.sla_deadline.isoformat() if a.sla_deadline else None,
        escalation_count=a.escalation_count or 0,
        assigned_to=str(a.assigned_to) if a.assigned_to else None,
        decided_by=str(a.decided_by) if a.decided_by else None,
        decided_at=a.decided_at.isoformat() if a.decided_at else None,
        decision_reason=a.decision_reason or "",
        created_at=a.created_at.isoformat() if a.created_at else None,
        updated_at=a.updated_at.isoformat() if a.updated_at else None,
    )


def _build_audit_trail(a: ApprovalRequestModel) -> list[AuditEntry]:
    trail: list[AuditEntry] = []

    trail.append(AuditEntry(
        action="created",
        performed_at=a.created_at.isoformat() if a.created_at else None,
        notes=f"Request created in category {_enum_val(a.category)} with risk {_enum_val(a.risk_level)}",
    ))

    if a.assigned_to:
        trail.append(AuditEntry(
            action="assigned",
            performed_by=str(a.assigned_to),
            notes="Request assigned",
        ))

    if a.status in (ApprovalStatusEnum.APPROVED, ApprovalStatusEnum.REJECTED) and a.decided_at:
        trail.append(AuditEntry(
            action=_enum_val(a.status),
            performed_by=str(a.decided_by) if a.decided_by else None,
            performed_at=a.decided_at.isoformat() if a.decided_at else None,
            notes=a.decision_reason or "",
        ))

    if a.escalation_count and a.escalation_count > 0:
        trail.append(AuditEntry(
            action="escalated",
            notes=f"Escalated {a.escalation_count} time(s)",
        ))

    return trail
