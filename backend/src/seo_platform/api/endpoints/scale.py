from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from seo_platform.services.scale_readiness import scale_readiness

router = APIRouter()


@router.get("/scale/tenant-capacity/{tenant_id}")
async def get_tenant_capacity(tenant_id: UUID) -> dict:
    report = await scale_readiness.analyze_tenant_capacity(tenant_id)
    return {"success": True, "data": report.model_dump()}


@router.get("/scale/recommendations")
async def get_scaling_recommendations() -> dict:
    recommendations = await scale_readiness.get_scaling_recommendations()
    return {"success": True, "data": recommendations.model_dump()}


@router.get("/scale/queue-partitions")
async def get_queue_partitions() -> dict:
    partitions = await scale_readiness.estimate_queue_partitions()
    return {
        "success": True,
        "data": [p.model_dump() for p in partitions],
        "count": len(partitions),
    }


@router.get("/scale/worker-scaling")
async def get_worker_scaling() -> dict:
    scaling = await scale_readiness.analyze_worker_scaling()
    return {
        "success": True,
        "data": [s.model_dump() for s in scaling],
        "count": len(scaling),
    }
