from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.global_infrastructure import global_infrastructure

router = APIRouter()


@router.get("/global-infra/regions")
async def get_all_region_deployments():
    """Return all region deployments with health and service instance data."""
    deployments = await global_infrastructure.get_all_region_deployments()
    return {"success": True, "data": [d.to_dict() for d in deployments]}


@router.get("/global-infra/workflow-replication")
async def get_cross_region_replication():
    """Return cross-region workflow replication status."""
    replications = await global_infrastructure.get_cross_region_replication_status()
    return {"success": True, "data": [r.to_dict() for r in replications]}


@router.get("/global-infra/queue-federation")
async def get_queue_federation():
    """Return distributed queue federation status across regions."""
    queues = await global_infrastructure.analyze_queue_federation()
    return {"success": True, "data": [q.to_dict() for q in queues]}


@router.post("/global-infra/failover-plan")
async def create_regional_failover_plan(
    source_region: str = Query(..., description="Source region to failover from"),
    target_region: str = Query(..., description="Target region to failover to"),
    reason: str = Query("scheduled_maintenance", description="Reason for failover"),
):
    """Generate a regional failover plan with rollback steps and validation checks."""
    plan = await global_infrastructure.plan_regional_failover(source_region, target_region, reason)
    return {"success": True, "data": plan.to_dict()}


@router.get("/global-infra/geo-routes")
async def get_geo_aware_routes():
    """Return geo-aware routing configuration for workflow types."""
    routes = await global_infrastructure.get_geo_aware_routes()
    return {"success": True, "data": [r.to_dict() for r in routes]}


@router.get("/global-infra/locality-intelligence")
async def get_infra_locality():
    """Return infrastructure locality intelligence and cross-region latency analysis."""
    locality = await global_infrastructure.analyze_infra_locality()
    return {"success": True, "data": locality.to_dict()}


@router.get("/global-infra/regional-observability")
async def get_regional_observability(
    region: str = Query("us-east-1", description="Region to observe"),
):
    """Return observability metrics and health trend for a specific region."""
    obs = await global_infrastructure.get_regional_observability(region)
    return {"success": True, "data": obs.to_dict()}


@router.get("/global-infra/active-active-topology")
async def get_active_active_topology():
    """Return active-active global topology with traffic distribution."""
    topology = await global_infrastructure.get_active_active_topology()
    return {"success": True, "data": topology.to_dict()}


@router.get("/global-infra/disaster-recovery")
async def assess_disaster_recovery(
    region: str = Query(..., description="Region to assess DR for"),
):
    """Return disaster recovery assessment for a specific region."""
    dr = await global_infrastructure.assess_disaster_recovery(region)
    return {"success": True, "data": dr.to_dict()}
