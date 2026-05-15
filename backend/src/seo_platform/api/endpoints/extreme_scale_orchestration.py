from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.extreme_scale_orchestration import extreme_scale_orchestration

router = APIRouter()


@router.get("/extreme-scale-orchestration/queue-partitioning")
async def get_queue_partitioning(
    queue_name: str = Query(..., description="Queue name"),
):
    result = await extreme_scale_orchestration.partition_ultra_scale_queues(queue_name)
    return {"success": True, "data": result.model_dump()}


@router.get("/extreme-scale-orchestration/orchestration-federation")
async def get_orchestration_federation(
    region: str = Query("us-east-1", description="Region to federate"),
):
    result = await extreme_scale_orchestration.federate_orchestration(region)
    return {"success": True, "data": result.model_dump()}


@router.get("/extreme-scale-orchestration/infrastructure-segmentation")
async def get_infrastructure_segmentation(
    tenant_id: str = Query(..., description="Tenant ID"),
):
    result = await extreme_scale_orchestration.segment_infrastructure(tenant_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/extreme-scale-orchestration/workflow-sharding")
async def get_workflow_sharding(
    workflow_type: str = Query(..., description="Workflow type"),
):
    result = await extreme_scale_orchestration.shard_workflows(workflow_type)
    return {"success": True, "data": result.model_dump()}


@router.get("/extreme-scale-orchestration/load-balance-plan")
async def get_load_balance_plan(
    cluster: str = Query("default", description="Cluster name"),
):
    result = await extreme_scale_orchestration.balance_operational_load(cluster)
    return {"success": True, "data": result.model_dump()}


@router.get("/extreme-scale-orchestration/capacity-forecast")
async def get_capacity_forecast(
    horizon_days: int = Query(90, ge=7, le=365),
):
    result = await extreme_scale_orchestration.forecast_orchestration_capacity(horizon_days)
    return {"success": True, "data": result.model_dump()}


@router.get("/extreme-scale-orchestration/distributed-execution-analysis")
async def get_distributed_execution_analysis(
    workflow_id: str = Query(..., description="Workflow ID"),
):
    result = await extreme_scale_orchestration.analyze_distributed_execution(workflow_id)
    return {"success": True, "data": result.model_dump()}
