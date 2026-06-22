from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from seo_platform.core.rbac import RequirePermission
from seo_platform.services.deployment_orchestration import deployment_orchestration

router = APIRouter()


@router.get("/health/{service_name}")
async def validate_deployment_health(
    service_name: str = Path(..., description="Service name to validate"),
    _auth: None = Depends(RequirePermission("system:write")),
):
    health = await deployment_orchestration.validate_deployment_health(service_name)
    return {"success": True, "data": health.to_dict()}


@router.get("/canary/{service_name}")
async def get_canary_status(
    service_name: str = Path(..., description="Service name for canary status"),
    _auth: None = Depends(RequirePermission("system:write")),
):
    status = await deployment_orchestration.get_canary_status(service_name)
    return {"success": True, "data": status.to_dict()}


@router.get("/blue-green")
async def get_blue_green_status(
    _auth: None = Depends(RequirePermission("system:write")),
):
    status = await deployment_orchestration.get_blue_green_status()
    return {"success": True, "data": status.to_dict()}


@router.get("/rollback-safety")
async def check_rollback_safety(
    target_version: str = Query(..., description="Target version to check rollback safety for"),
    _auth: None = Depends(RequirePermission("system:write")),
):
    safety = await deployment_orchestration.check_rollback_safety(target_version)
    return {"success": True, "data": safety.to_dict()}


@router.get("/history/{service_name}")
async def get_deployment_history(
    service_name: str = Path(..., description="Service name"),
    limit: int = Query(10, ge=1, le=100, description="Number of entries"),
    _auth: None = Depends(RequirePermission("system:write")),
):
    history = await deployment_orchestration.get_deployment_history(service_name, limit=limit)
    return {"success": True, "data": [h.to_dict() for h in history], "count": len(history)}


# ---------------------------------------------------------------------------
# Phase 4 — Production Deployment Dominance Endpoints
# ---------------------------------------------------------------------------


@router.get("/topology")
async def get_production_topology(
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Return full production topology with service instances, autoscaling groups, and load balancers."""
    topology = await deployment_orchestration.get_production_topology()
    return {"success": True, "data": topology.to_dict()}


@router.get("/autoscaling-optimization")
async def get_autoscaling_optimization(
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Analyze autoscaling performance and provide optimization recommendations."""
    optimization = await deployment_orchestration.optimize_autoscaling()
    return {"success": True, "data": optimization.to_dict()}


@router.get("/multi-region-readiness")
async def get_multi_region_readiness(
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Assess multi-region deployment readiness and failover capability."""
    readiness = await deployment_orchestration.assess_multi_region_readiness()
    return {"success": True, "data": readiness.to_dict()}


@router.post("/failover-plan")
async def create_failover_plan(
    region_from: str = Query(..., description="Source region"),
    region_to: str = Query(..., description="Target region"),
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Generate a failover orchestration plan between regions."""
    plan = await deployment_orchestration.plan_failover(region_from, region_to)
    return {"success": True, "data": plan.to_dict()}


@router.get("/rollback-safety-report")
async def get_rollback_safety_report(
    deployment_id: str = Query(..., description="Deployment ID to validate"),
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Comprehensive rollback safety check for a specific deployment."""
    report = await deployment_orchestration.validate_rollback_safety(deployment_id)
    return {"success": True, "data": report.to_dict()}


@router.get("/infra-versions")
async def get_infra_versions(
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Track infrastructure versioning across all services."""
    report = await deployment_orchestration.track_infra_versioning()
    return {"success": True, "data": report.to_dict()}


@router.post("/blue-green-plan")
async def create_blue_green_plan(
    service_name: str = Query(..., description="Service name"),
    new_version: str = Query(..., description="New version to deploy"),
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Generate a blue/green rollout plan with traffic shift schedule."""
    plan = await deployment_orchestration.plan_blue_green_rollout(service_name, new_version)
    return {"success": True, "data": plan.to_dict()}


@router.get("/canary-analysis")
async def get_canary_analysis(
    canary_id: str = Query(..., description="Canary deployment ID"),
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Analyze canary deployment metrics and provide promotion/rollback recommendation."""
    analysis = await deployment_orchestration.analyze_canary(canary_id)
    return {"success": True, "data": analysis.to_dict()}


@router.get("/intelligence")
async def get_deployment_intelligence(
    _auth: None = Depends(RequirePermission("system:write")),
):
    """Return operational deployment intelligence including frequency, failure rate, and trends."""
    intelligence = await deployment_orchestration.generate_deployment_intelligence()
    return {"success": True, "data": intelligence.to_dict()}
