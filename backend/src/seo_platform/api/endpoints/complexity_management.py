from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import APIRouter, Body, Query

from seo_platform.services.complexity_management import complexity_management

router = APIRouter()


@router.get("/summary")
async def get_operational_summary(
    tenant_id: UUID | None = Query(None, description="Tenant UUID"),
):
    summary = await complexity_management.summarize_operational_state(tenant_id)
    return {"success": True, "data": summary.to_dict()}


@router.get("/workflow-summary")
async def get_workflow_summary(
    tenant_id: UUID | None = Query(None, description="Tenant UUID"),
):
    summary = await complexity_management.summarize_workflow_state(tenant_id)
    return {"success": True, "data": summary.to_dict()}


@router.get("/executive-telemetry")
async def get_executive_telemetry(
    tenant_id: UUID | None = Query(None, description="Tenant UUID"),
):
    telemetry = await complexity_management.get_executive_telemetry(tenant_id)
    return {"success": True, "data": telemetry.to_dict()}


@router.get("/workflow-groups")
async def get_workflow_groups(
    tenant_id: UUID | None = Query(None, description="Tenant UUID"),
):
    groups = await complexity_management.group_workflows_by_state(tenant_id)
    return {"success": True, "data": groups.to_dict()}


@router.get("/dashboard-config")
async def get_dashboard_config(
    tenant_id: UUID | None = Query(None, description="Tenant UUID"),
    role: str = Query("operator", description="User role: operator | executive | developer"),
):
    config = await complexity_management.get_dashboard_config(tenant_id, role=role)
    return {"success": True, "data": config.to_dict()}


@router.get("/prioritized-alerts")
async def get_prioritized_alerts():
    prioritized = await complexity_management.prioritize_alerts()
    return {"success": True, "data": prioritized.to_dict()}


@router.post("/suppress-alerts")
async def suppress_alerts(
    alerts: list[dict] = Body(..., description="Alerts to suppress"),
    time_window_hours: int = Body(1, description="Deduplication window in hours"),
):
    filtered = await complexity_management.suppress_noise_alerts(
        alerts=alerts,
        time_window_hours=time_window_hours,
    )
    return {"success": True, "data": filtered, "count": len(filtered)}
