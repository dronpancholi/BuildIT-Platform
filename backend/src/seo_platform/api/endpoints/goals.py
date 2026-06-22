"""
SEO Platform — Phase 14 API: Goal Orchestration Endpoints
===================================================================
Allows users to create, query, pause, resume, and cancel goal executions.
All endpoints are tenant‑scoped, enforce RBAC, rate limiting, and audit logging.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import uuid
from datetime import datetime
from typing import List, Mapping, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse
from seo_platform.core.auth import get_current_user, get_validated_tenant_id
from seo_platform.core.logging import get_logger
from seo_platform.services.orchestrator import orchestrator_service
from seo_platform.core.database import get_tenant_session
from sqlalchemy import select
from seo_platform.models.goal import GoalExecution, GoalState

router = APIRouter()
logger = get_logger(__name__)

# Helper: convert GoalExecution to API model
def _goal_to_response(goal: GoalExecution) -> GoalResponse:
    data = {
        "id": goal.id,
        "tenant_id": goal.tenant_id,
        "definition_id": goal.definition_id,
        "state": goal.state.value if hasattr(goal.state, "value") else str(goal.state),
        "metadata": goal.metadata_json or {},
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
        "started_at": goal.started_at.isoformat() if goal.started_at else None,
        "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
        "result": goal.outcome_summary or None,
    }
    return GoalResponse(**data)

# ---------------------------------------------------------------------------
# Helper RBAC (reuse same logic as agents endpoint)
# ---------------------------------------------------------------------------
def _require_admin(user = Depends(get_current_user)):
    if user.role not in {"super_admin", "admin", "manager"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class GoalCreateRequest(BaseModel):
    definition_id: uuid.UUID = Field(..., description="GoalDefinition UUID")
    metadata: Mapping[str, Any] | None = None

class GoalResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    definition_id: uuid.UUID
    state: str
    metadata: Mapping[str, Any]
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    result: Mapping[str, Any] | None = None

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=APIResponse[GoalResponse], status_code=201)
async def create_goal(request: GoalCreateRequest, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[GoalResponse]:
    from seo_platform.core.sanitization import sanitize_dict

    sanitized_metadata = sanitize_dict(dict(request.metadata)) if request.metadata else {}
    goal = await orchestrator_service.start_goal(
        tenant_id=tenant_id,
        user_id=user.id,
        goal_definition_id=request.definition_id,
        metadata=sanitized_metadata,
    )
    return APIResponse(data=_goal_to_response(goal))

@router.get("", response_model=APIResponse[list[GoalResponse]])
async def list_goals(tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[list[GoalResponse]]:
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(select(GoalExecution).where(GoalExecution.tenant_id == tenant_id))
        goals = result.scalars().all()
        return APIResponse(data=[_goal_to_response(g) for g in goals])

@router.get("/{goal_id}", response_model=APIResponse[GoalResponse])
async def get_goal(goal_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[GoalResponse]:
    goal = await orchestrator_service.get_goal_status(tenant_id, goal_id)
    return APIResponse(data=_goal_to_response(goal))

@router.post("/{goal_id}/pause", response_model=APIResponse[GoalResponse])
async def pause_goal(goal_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[GoalResponse]:
    goal = await orchestrator_service.pause_goal(tenant_id, goal_id, user.id)
    return APIResponse(data=_goal_to_response(goal))

@router.post("/{goal_id}/resume", response_model=APIResponse[GoalResponse])
async def resume_goal(goal_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[GoalResponse]:
    goal = await orchestrator_service.resume_goal(tenant_id, goal_id, user.id)
    return APIResponse(data=_goal_to_response(goal))

@router.post("/{goal_id}/cancel", response_model=APIResponse[GoalResponse])
async def cancel_goal(goal_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[GoalResponse]:
    goal = await orchestrator_service.cancel_goal(tenant_id, goal_id, user.id)
    return APIResponse(data=_goal_to_response(goal))

