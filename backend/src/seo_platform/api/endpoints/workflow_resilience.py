from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

from seo_platform.services.workflow_resilience import workflow_resilience

router = APIRouter()


class InvariantValidationRequest(BaseModel):
    workflow_id: str
    expected_state: str | None = None


class RemediateRequest(BaseModel):
    workflow_id: str
    action: str  # cancel | reset | restart | archive


@router.get("/workflow-resilience/health")
async def get_workflow_health(tenant_id: UUID | None = Query(None)) -> dict:
    reports = await workflow_resilience.score_workflow_health(tenant_id)
    return {"success": True, "data": [r.to_dict() for r in reports], "count": len(reports)}


@router.get("/workflow-resilience/lifecycle-analytics")
async def get_lifecycle_analytics(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    analytics = await workflow_resilience.analyze_workflow_lifecycle(time_window_hours)
    return {"success": True, "data": analytics.to_dict()}


@router.get("/workflow-resilience/orphans")
async def get_orphan_workflows() -> dict:
    orphans = await workflow_resilience.detect_orphan_workflows()
    return {"success": True, "data": [o.to_dict() for o in orphans], "count": len(orphans)}


@router.post("/workflow-resilience/cleanup-orphans")
async def cleanup_orphan_workflows() -> dict:
    report = await workflow_resilience.cleanup_orphan_workflows()
    return {"success": True, "data": report.to_dict()}


@router.post("/workflow-resilience/validate-replay")
async def validate_replay_safety() -> dict:
    report = await workflow_resilience.validate_replay_safety()
    return {"success": True, "data": report.to_dict()}


@router.post("/workflow-resilience/validate-invariants")
async def validate_invariants(request: InvariantValidationRequest) -> dict:
    result = await workflow_resilience.validate_execution_invariants(
        request.workflow_id, request.expected_state,
    )
    return {"success": True, "data": result.to_dict()}


@router.get("/workflow-resilience/dead-letter")
async def get_dead_letter_workflows() -> dict:
    dead_letters = await workflow_resilience.detect_dead_letter_workflows()
    return {"success": True, "data": [d.to_dict() for d in dead_letters], "count": len(dead_letters)}


@router.post("/workflow-resilience/remediate")
async def remediate_dead_letter_workflow(request: RemediateRequest) -> dict:
    result = await workflow_resilience.remediate_dead_letter_workflow(
        request.workflow_id, request.action,
    )
    return {"success": True, "data": result.to_dict()}
