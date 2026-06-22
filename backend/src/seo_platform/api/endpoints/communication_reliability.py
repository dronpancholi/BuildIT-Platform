from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, Body, Query

from seo_platform.services.communication_reliability import communication_reliability

router = APIRouter()


@router.post("/retry")
async def orchestrate_retry(
    tenant_id: UUID = Body(..., embed=True),
    communication_id: str = Body(..., embed=True),
    max_attempts: int = Body(3, embed=True),
) -> dict:
    result = await communication_reliability.orchestrate_communication_retry(
        tenant_id, communication_id, max_attempts,
    )
    return {"success": True, "data": result.model_dump()}


@router.get("/delivery-analytics")
async def get_delivery_analytics(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    time_window_hours: int = Query(168, description="Time window in hours"),
) -> dict:
    analytics = await communication_reliability.get_delivery_analytics(tenant_id, time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.post("/sync-responses")
async def sync_responses(
    tenant_id: UUID = Body(..., embed=True),
    campaign_id: UUID = Body(..., embed=True),
) -> dict:
    result = await communication_reliability.synchronize_responses(tenant_id, campaign_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/replay-safety")
async def get_replay_safety(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    campaign_id: UUID = Query(..., description="Campaign UUID"),
) -> dict:
    report = await communication_reliability.validate_communication_replay_safety(tenant_id, campaign_id)
    return {"success": True, "data": report.model_dump()}


@router.get("/provider-health")
async def get_provider_health(
    provider_name: str = Query(..., description="Provider name"),
) -> dict:
    health = await communication_reliability.check_provider_health(provider_name)
    return {"success": True, "data": health.model_dump()}


@router.post("/failover")
async def failover_provider(
    tenant_id: UUID = Body(..., embed=True),
    campaign_id: UUID = Body(..., embed=True),
    current_provider: str = Body(..., embed=True),
) -> dict:
    result = await communication_reliability.failover_provider(tenant_id, campaign_id, current_provider)
    return {"success": True, "data": result.model_dump()}


@router.get("/bounce-intelligence")
async def get_bounce_intelligence(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    time_window_hours: int = Query(168, description="Time window in hours"),
) -> dict:
    intelligence = await communication_reliability.analyze_bounces(tenant_id, time_window_hours)
    return {"success": True, "data": intelligence.model_dump()}


@router.post("/suppress-bounces")
async def suppress_bounces() -> dict:
    count = await communication_reliability.suppress_bounced_addresses()
    return {"success": True, "data": {"suppress_count": count}}


@router.get("/workflow-consistency")
async def get_workflow_consistency(
    workflow_run_id: str = Query(..., description="Workflow run ID"),
) -> dict:
    report = await communication_reliability.check_workflow_communication_consistency(workflow_run_id)
    return {"success": True, "data": report.model_dump()}
