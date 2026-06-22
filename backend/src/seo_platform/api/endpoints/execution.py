"""
SEO Platform — Phase 14 API: Execution Engine Endpoints
=====================================================
Schedule and monitor action executions.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import uuid
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse
from seo_platform.core.rbac import RequirePermission
from seo_platform.services.execution_engine import execution_engine
from seo_platform.models.action import ActionExecution, ActionExecutionStatus
from seo_platform.core.database import get_tenant_session

router = APIRouter()


class ExecutionRequest(BaseModel):
    tenant_id: uuid.UUID
    action_name: str
    input_data: Mapping[str, Any] = Field(default_factory=dict)
    correlation_id: uuid.UUID | None = None


class ExecutionResponse(BaseModel):
    id: uuid.UUID
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    output_data: dict[str, Any] | None = None


@router.get("", response_model=APIResponse[list[ExecutionResponse]])
async def list_executions(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _auth: None = Depends(RequirePermission("execution:read")),
) -> APIResponse[list[ExecutionResponse]]:
    """List executions for a tenant with pagination."""
    from sqlalchemy import func, select
    from seo_platform.models.action import ActionExecution

    async with get_tenant_session(tenant_id) as session:
        stmt = (
            select(ActionExecution)
            .where(ActionExecution.tenant_id == tenant_id)
            .order_by(ActionExecution.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(ActionExecution).where(ActionExecution.tenant_id == tenant_id)

        result = await session.execute(stmt)
        executions = result.scalars().all()
        count_result = await session.execute(count_stmt)
        total = count_result.scalar_one()

        return APIResponse(
            data=[
                ExecutionResponse(
                    id=e.id,
                    status=e.status.value,
                    started_at=e.started_at.isoformat() if e.started_at else None,
                    completed_at=e.completed_at.isoformat() if e.completed_at else None,
                    error_message=e.error_message,
                    output_data=e.output_data,
                )
                for e in executions
            ],
            meta={"total": total, "offset": offset, "limit": limit},
        )


@router.post("", response_model=APIResponse[ExecutionResponse], status_code=202)
async def schedule_execution(request: ExecutionRequest, user = Depends(RequirePermission("execution:write"))) -> APIResponse[ExecutionResponse]:
    execution = await execution_engine.schedule_execution(
        tenant_id=request.tenant_id,
        action_name=request.action_name,
        input_data=request.input_data,
        correlation_id=request.correlation_id,
    )
    resp = ExecutionResponse(
        id=execution.id,
        status=execution.status.value,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        error_message=execution.error_message,
        output_data=execution.output_data,
    )
    return APIResponse(data=resp)


@router.get("/{execution_id}", response_model=APIResponse[ExecutionResponse])
async def get_execution(execution_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(RequirePermission("execution:read"))) -> APIResponse[ExecutionResponse]:
    async with get_tenant_session(tenant_id) as session:
        execution = await session.get(ActionExecution, execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        resp = ExecutionResponse(
            id=execution.id,
            status=execution.status.value,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            error_message=execution.error_message,
            output_data=execution.output_data,
        )
        return APIResponse(data=resp)
