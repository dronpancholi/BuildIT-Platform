from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.cross_tenant_intelligence import cross_tenant_intelligence

router = APIRouter()


@router.get("/cross-tenant/benchmarks")
async def get_benchmarks(
    metric: str | None = Query(None),
) -> dict:
    benchmarks = await cross_tenant_intelligence.get_anonymized_benchmarks(metric)
    return {
        "success": True,
        "data": [b.model_dump() for b in benchmarks],
        "count": len(benchmarks),
    }


@router.get("/cross-tenant/analytics")
async def get_analytics() -> dict:
    analytics = await cross_tenant_intelligence.get_cross_tenant_analytics()
    return {"success": True, "data": analytics.model_dump()}


@router.get("/cross-tenant/workflow-baselines")
async def get_workflow_baselines(
    workflow_type: str | None = Query(None),
) -> dict:
    baselines = await cross_tenant_intelligence.get_global_workflow_baselines(workflow_type)
    return {
        "success": True,
        "data": [b.model_dump() for b in baselines],
        "count": len(baselines),
    }


@router.get("/cross-tenant/anomaly-comparison")
async def get_anomaly_comparison(
    tenant_id: UUID = Query(...),
    anomaly_type: str = Query(...),
) -> dict:
    comparison = await cross_tenant_intelligence.compare_anomaly_to_benchmark(
        tenant_id, anomaly_type,
    )
    return {"success": True, "data": comparison.model_dump()}


@router.get("/cross-tenant/infrastructure-utilization")
async def get_infrastructure_utilization() -> dict:
    utilization = await cross_tenant_intelligence.get_infrastructure_utilization_intelligence()
    return {
        "success": True,
        "data": [u.model_dump() for u in utilization],
        "count": len(utilization),
    }


@router.get("/cross-tenant/operational-trends")
async def get_operational_trends(
    metric: str = Query(...),
    timeframe: str = Query("24h"),
) -> dict:
    trend = await cross_tenant_intelligence.analyze_enterprise_operational_trends(
        metric, timeframe,
    )
    return {"success": True, "data": trend.model_dump()}


@router.get("/cross-tenant/tenant-benchmarks")
async def get_tenant_benchmarks(
    tenant_id: UUID = Query(...),
) -> dict:
    benchmarks = await cross_tenant_intelligence.get_tenant_operational_benchmarks(tenant_id)
    return {"success": True, "data": benchmarks}
