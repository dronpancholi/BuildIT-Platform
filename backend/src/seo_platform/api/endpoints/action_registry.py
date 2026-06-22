"""
SEO Platform — Phase 14 API: Action Registry Endpoints
=====================================================
CRUD operations for the ActionDefinition catalog.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse, ResponseMeta
from seo_platform.core.rbac import RequirePermission
from seo_platform.services.action_registry import action_registry_service

router = APIRouter()


class ActionDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    category: str = Field(..., description="One of: crm, campaign, communication, analytics, workflow, integration")
    risk_level: str = Field(..., description="low | medium | high | critical")
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    permission_required: str = Field(...)
    requires_approval: bool = True
    approval_policy: dict[str, Any] | None = None
    rollback_handler: str | None = None
    execution_timeout_seconds: int = 300
    max_retries: int = 3
    idempotent: bool = False
    is_enabled: bool = True
    version: int = 1
    custom_metadata: dict[str, Any] | None = None


class ActionDefinitionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    display_name: str
    description: str
    category: str
    risk_level: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    permission_required: str
    requires_approval: bool
    approval_policy: dict[str, Any] | None
    rollback_handler: str | None
    execution_timeout_seconds: int
    max_retries: int
    idempotent: bool
    is_enabled: bool
    version: int
    custom_metadata: dict[str, Any] | None
    created_at: str | None = None
    updated_at: str | None = None


@router.get("", response_model=APIResponse[list[ActionDefinitionResponse]])
async def list_actions(tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(RequirePermission("action:read"))) -> APIResponse[list[ActionDefinitionResponse]]:
    actions = await action_registry_service.list_actions(tenant_id)
    resp = [ActionDefinitionResponse(**action.__dict__) for action in actions]
    return APIResponse(data=resp)


@router.post("", response_model=APIResponse[ActionDefinitionResponse], status_code=201)
async def create_action(request: ActionDefinitionCreate, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(RequirePermission("action:write"))) -> APIResponse[ActionDefinitionResponse]:
    data = request.model_dump()
    action = await action_registry_service.create_action(tenant_id, data)
    resp = ActionDefinitionResponse(**action.__dict__)
    return APIResponse(data=resp)


@router.get("/{action_id}", response_model=APIResponse[ActionDefinitionResponse])
async def get_action(action_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(RequirePermission("action:read"))) -> APIResponse[ActionDefinitionResponse]:
    action = await action_registry_service.get_action(tenant_id, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    resp = ActionDefinitionResponse(**action.__dict__)
    return APIResponse(data=resp)


@router.put("/{action_id}", response_model=APIResponse[ActionDefinitionResponse])
async def update_action(action_id: uuid.UUID, request: ActionDefinitionCreate, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(RequirePermission("action:write"))) -> APIResponse[ActionDefinitionResponse]:
    data = request.model_dump(exclude_unset=True)
    action = await action_registry_service.update_action(tenant_id, action_id, data)
    resp = ActionDefinitionResponse(**action.__dict__)
    return APIResponse(data=resp)


@router.delete("/{action_id}", response_model=APIResponse[ActionDefinitionResponse])
async def disable_action(action_id: uuid.UUID, tenant_id: uuid.UUID = Depends(get_validated_tenant_id), user = Depends(RequirePermission("action:delete"))) -> APIResponse[ActionDefinitionResponse]:
    action = await action_registry_service.disable_action(tenant_id, action_id)
    resp = ActionDefinitionResponse(**action.__dict__)
    return APIResponse(data=resp)
