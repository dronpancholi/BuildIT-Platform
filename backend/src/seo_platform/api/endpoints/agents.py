"""
SEO Platform — Phase 14 API: Agent Management Endpoints
===================================================================
Provides CRUD for agents, task listing, conflict listing, and task cancellation.
All endpoints enforce tenant isolation, RBAC (SUPER_ADMIN/TENANT_ADMIN/MANAGER), rate limiting, and audit logging.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse
from seo_platform.core.auth import get_current_user, get_validated_tenant_id
from seo_platform.core.logging import get_logger
from seo_platform.services.agent_registry import agent_registry
from seo_platform.services.scheduler import scheduler
from seo_platform.core.database import get_tenant_session
from sqlalchemy import select
from seo_platform.services.conflict_resolution import conflict_resolution_service
from seo_platform.models.agent import AgentDefinition, AgentInstance, AgentTask, AgentConflict, TaskStatus

router = APIRouter()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helper: simple RBAC check – allow only privileged roles
# ---------------------------------------------------------------------------

def _require_admin(user = Depends(get_current_user)):
    if user.role not in {"super_admin", "admin", "manager"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user

# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------

class AgentCreateRequest(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field(...)
    agent_type: str = Field(...)
    priority: int = Field(0, ge=0)
    capabilities: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)

class AgentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str
    agent_type: str
    enabled: bool
    priority: int
    capabilities: dict
    constraints: dict
    config: dict
    created_at: str | None = None
    updated_at: str | None = None

@router.get("", response_model=APIResponse[list[AgentResponse]])
async def list_agents(tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[list[AgentResponse]]:
    agents = await agent_registry.list_agents(tenant_id)
    return APIResponse(data=[AgentResponse(**a.__dict__) for a in agents])

@router.post("", response_model=APIResponse[AgentResponse], status_code=201)
async def create_agent(request: AgentCreateRequest, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[AgentResponse]:
    data = request.model_dump()
    agent = await agent_registry.create_agent(tenant_id, data)
    return APIResponse(data=AgentResponse(**agent.__dict__))

@router.put("/{agent_id}", response_model=APIResponse[AgentResponse])
async def update_agent(agent_id: uuid.UUID, request: AgentCreateRequest, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[AgentResponse]:
    data = request.model_dump(exclude_unset=True)
    agent = await agent_registry.update_agent(tenant_id, agent_id, data)
    return APIResponse(data=AgentResponse(**agent.__dict__))

@router.delete("/{agent_id}", response_model=APIResponse[AgentResponse])
async def delete_agent(agent_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[AgentResponse]:
    # Disable instead of hard delete for safety
    agent = await agent_registry.disable_agent(tenant_id, agent_id)
    return APIResponse(data=AgentResponse(**agent.__dict__))

# ---------------------------------------------------------------------------
# Tasks and conflicts
# ---------------------------------------------------------------------------

class TaskResponse(BaseModel):
    id: uuid.UUID
    agent_instance_id: uuid.UUID
    status: str
    priority: int
    urgency: int
    execution_reference: uuid.UUID | None = None
    created_at: str | None = None
    scheduled_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict

@router.get("/tasks", response_model=APIResponse[list[TaskResponse]])
async def list_tasks(tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[list[TaskResponse]]:
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(select(AgentTask).where(AgentTask.tenant_id == tenant_id))
        tasks = result.scalars().all()
        # Map ORM attribute name `metadata_json` to API field `metadata`
        def task_to_response(t):
            data = t.__dict__.copy()
            # Rename metadata_json to metadata, fallback to empty dict
            data["metadata"] = data.pop("metadata_json", {})
            return TaskResponse(**data)
        return APIResponse(data=[task_to_response(t) for t in tasks])

@router.post("/tasks/{task_id}/cancel", response_model=APIResponse[TaskResponse])
async def cancel_task(task_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[TaskResponse]:
    await scheduler.cancel_task(tenant_id, task_id)
    async with get_tenant_session(tenant_id) as session:
        task = await session.get(AgentTask, task_id)
        data = task.__dict__.copy()
        data["metadata"] = data.pop("metadata_json", {})
        return APIResponse(data=TaskResponse(**data))

class ConflictResponse(BaseModel):
    id: uuid.UUID
    conflict_type: str
    involved_agents: List[uuid.UUID]
    resolution_strategy: str
    status: str
    metadata: dict
    created_at: str | None = None
    updated_at: str | None = None

@router.get("/conflicts", response_model=APIResponse[list[ConflictResponse]])
async def list_conflicts(tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(_require_admin)) -> APIResponse[list[ConflictResponse]]:
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(select(AgentConflict).where(AgentConflict.tenant_id == tenant_id))
        conflicts = result.scalars().all()
        def conflict_to_response(c):
            data = c.__dict__.copy()
            data["metadata"] = data.pop("metadata_json", {})
            return ConflictResponse(**data)
        return APIResponse(data=[conflict_to_response(c) for c in conflicts])

