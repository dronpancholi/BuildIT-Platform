"""
SEO Platform — Kill Switch API
=================================
Emergency operations control — expose kill switch state and mutations
to the frontend Mission Control console.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.kill_switch import kill_switch_service
from seo_platform.schemas import APIResponse

router = APIRouter()


class ActivateRequest(BaseModel):
    switch_key: str = Field(..., min_length=1)
    reason: str = Field(default="Manual activation via console")
    activated_by: str = Field(default="console_admin")
    auto_reset_seconds: int | None = None


class DeactivateRequest(BaseModel):
    switch_key: str = Field(..., min_length=1)
    deactivated_by: str = Field(default="console_admin")


@router.get("", response_model=APIResponse[list[dict]])
async def list_active_kill_switches() -> APIResponse[list[dict]]:
    """List all currently active kill switches from Redis."""
    switches = await kill_switch_service.list_active()
    return APIResponse(data=switches)


@router.post("/activate", response_model=APIResponse[dict])
async def activate_kill_switch(
    request: ActivateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Activate an emergency kill switch. Takes immediate effect."""
    await kill_switch_service.activate(
        switch_key=request.switch_key,
        reason=request.reason,
        activated_by=str(current_user.id),
        auto_reset_seconds=request.auto_reset_seconds,
    )
    return APIResponse(data={
        "switch_key": request.switch_key,
        "status": "activated",
        "reason": request.reason,
    })


@router.post("/deactivate", response_model=APIResponse[dict])
async def deactivate_kill_switch(
    request: DeactivateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Deactivate an emergency kill switch. Restores normal operations."""
    await kill_switch_service.deactivate(
        switch_key=request.switch_key,
        deactivated_by=str(current_user.id),
    )
    return APIResponse(data={
        "switch_key": request.switch_key,
        "status": "deactivated",
    })
