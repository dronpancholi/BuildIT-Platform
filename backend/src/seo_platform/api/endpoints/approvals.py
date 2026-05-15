"""
SEO Platform — Approval Endpoints
=====================================
Approval queue management and decision submission.
"""

from __future__ import annotations

from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse

router = APIRouter()


class ApprovalRequestResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    workflow_run_id: str
    category: str
    risk_level: str
    status: str
    summary: str
    ai_risk_summary: str
    sla_deadline: str | None
    escalation_count: int
    context_snapshot: dict = Field(default_factory=dict)


class SubmitDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected|modification_requested)$")
    decided_by: UUID
    reason: str = ""
    modifications: dict = Field(default_factory=dict)


@router.get("", response_model=APIResponse[list[ApprovalRequestResponse]])
async def list_pending_approvals(
    tenant_id: UUID = Query(...),
    risk_level: str | None = Query(default=None),
) -> APIResponse[list[ApprovalRequestResponse]]:
    """List pending approval requests for a tenant, sorted by priority."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.approval import ApprovalRequestModel, ApprovalStatusEnum

    async with get_tenant_session(tenant_id) as session:
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.tenant_id == tenant_id,
            ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
        ).order_by(ApprovalRequestModel.created_at.asc())

        result = await session.execute(stmt)
        requests = result.scalars().all()

        return APIResponse(
            data=[
                ApprovalRequestResponse(
                    id=r.id,
                    tenant_id=r.tenant_id,
                    workflow_run_id=r.workflow_run_id,
                    category=r.category.value,
                    risk_level=r.risk_level.value,
                    status=r.status.value,
                    summary=r.summary,
                    ai_risk_summary=r.ai_risk_summary,
                    sla_deadline=r.sla_deadline.isoformat() if r.sla_deadline else None,
                    escalation_count=r.escalation_count,
                    context_snapshot=r.context_snapshot,
                )
                for r in requests
            ]
        )


@router.post("/{request_id}/decide", response_model=APIResponse[dict])
async def submit_decision(
    request_id: UUID,
    body: SubmitDecisionRequest,
    tenant_id: UUID = Query(...),
) -> APIResponse[dict]:
    """Submit an approval decision. Signals the waiting Temporal workflow."""
    from datetime import datetime

    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.approval import ApprovalRequestModel, ApprovalStatusEnum
    from seo_platform.services.approval import ApprovalDecision as ServiceApprovalDecision
    from seo_platform.services.approval import approval_service

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(ApprovalRequestModel).where(
                ApprovalRequestModel.id == request_id,
                ApprovalRequestModel.tenant_id == tenant_id,
            )
        )
        request = result.scalar_one_or_none()
        if not request:
            raise HTTPException(status_code=404, detail="Approval request not found")
        if request.status != ApprovalStatusEnum.PENDING:
            raise HTTPException(status_code=409, detail="Request already decided")

        request.status = ApprovalStatusEnum(body.decision)
        request.decided_by = body.decided_by
        request.decided_at = datetime.now(UTC)
        request.decision_reason = body.reason
        request.modifications = body.modifications

        decision = ServiceApprovalDecision(
            request_id=request_id,
            decision=ApprovalStatusEnum(body.decision).value,
            decided_by=str(body.decided_by),
            reason=body.reason,
            modifications=body.modifications,
        )

        await approval_service.decide(decision, request.workflow_run_id, tenant_id)

        return APIResponse(
            data={
                "request_id": str(request_id),
                "decision": body.decision,
                "workflow_run_id": request.workflow_run_id,
            }
        )
