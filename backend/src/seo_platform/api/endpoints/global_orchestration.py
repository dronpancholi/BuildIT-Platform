from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.global_orchestration import global_orchestration

router = APIRouter()


@router.get("/global-orchestration/federation")
async def get_workflow_federation():
    """Return workflow federation status across global regions."""
    federation = await global_orchestration.get_workflow_federation()
    return {"success": True, "data": federation.to_dict()}


@router.get("/global-orchestration/cross-cluster")
async def get_cross_cluster_coordination():
    """Return cross-cluster workflow coordination status."""
    coordinations = await global_orchestration.get_cross_cluster_coordination()
    return {"success": True, "data": [c.to_dict() for c in coordinations]}


@router.post("/global-orchestration/global-replay")
async def orchestrate_global_replay(
    workflow_type: str = Query(..., description="Workflow type to replay"),
    regions: str = Query("us-east-1,us-west-2", description="Comma-separated list of regions"),
):
    """Orchestrate a global replay to verify workflow consistency across regions."""
    region_list = [r.strip() for r in regions.split(",") if r.strip()]
    replay = await global_orchestration.orchestrate_global_replay(workflow_type, region_list)
    return {"success": True, "data": replay.to_dict()}


@router.get("/global-orchestration/distributed-intelligence")
async def get_distributed_workflow_intelligence(
    workflow_type: str = Query(..., description="Workflow type to analyze"),
):
    """Return distributed workflow execution intelligence for a workflow type."""
    intel = await global_orchestration.get_distributed_workflow_intelligence(workflow_type)
    return {"success": True, "data": intel.to_dict()}


@router.post("/global-orchestration/migration-plan")
async def plan_workflow_migration(
    source_cluster: str = Query(..., description="Source Temporal cluster"),
    target_cluster: str = Query(..., description="Target Temporal cluster"),
):
    """Generate a workflow migration plan between Temporal clusters."""
    plan = await global_orchestration.plan_workflow_migration(source_cluster, target_cluster)
    return {"success": True, "data": plan.to_dict()}


@router.get("/global-orchestration/partition-intelligence")
async def get_workflow_partition_intelligence(
    workflow_type: str = Query(..., description="Workflow type to analyze"),
):
    """Return workflow partition intelligence with hotspot detection."""
    partition = await global_orchestration.analyze_workflow_partitioning(workflow_type)
    return {"success": True, "data": partition.to_dict()}


@router.get("/global-orchestration/global-topology")
async def get_global_workflow_topology():
    """Return global workflow topology with interdependencies and critical paths."""
    topology = await global_orchestration.get_global_workflow_topology()
    return {"success": True, "data": topology.to_dict()}


@router.get("/global-orchestration/federation-analytics")
async def get_orchestration_federation_analytics():
    """Return orchestration federation analytics and recommendations."""
    analytics = await global_orchestration.get_orchestration_federation_analytics()
    return {"success": True, "data": analytics.to_dict()}
