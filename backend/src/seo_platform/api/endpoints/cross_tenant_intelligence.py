from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from seo_platform.services.cross_tenant_intelligence import cross_tenant_intelligence

router = APIRouter()


@router.get("/benchmarks")
async def get_benchmarks(
    metric: str | None = Query(None),
) -> dict:
    benchmarks = await cross_tenant_intelligence.get_anonymized_benchmarks(metric)
    return {
        "success": True,
        "data": [b.model_dump() for b in benchmarks],
        "count": len(benchmarks),
    }


@router.get("/analytics")
async def get_analytics() -> dict:
    analytics = await cross_tenant_intelligence.get_cross_tenant_analytics()
    return {"success": True, "data": analytics.model_dump()}


@router.get("/workflow-baselines")
async def get_workflow_baselines(
    workflow_type: str | None = Query(None),
) -> dict:
    baselines = await cross_tenant_intelligence.get_global_workflow_baselines(workflow_type)
    return {
        "success": True,
        "data": [b.model_dump() for b in baselines],
        "count": len(baselines),
    }


@router.get("/anomaly-comparison")
async def get_anomaly_comparison(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    anomaly_type: str = Query(...),
) -> dict:
    comparison = await cross_tenant_intelligence.compare_anomaly_to_benchmark(
        tenant_id, anomaly_type,
    )
    return {"success": True, "data": comparison.model_dump()}


@router.get("/infrastructure-utilization")
async def get_infrastructure_utilization() -> dict:
    utilization = await cross_tenant_intelligence.get_infrastructure_utilization_intelligence()
    return {
        "success": True,
        "data": [u.model_dump() for u in utilization],
        "count": len(utilization),
    }


@router.get("/operational-trends")
async def get_operational_trends(
    metric: str | None = Query(None),
    timeframe: str = Query("24h"),
) -> dict:
    metrics = [metric] if metric else ["workflow_count", "success_rate", "worker_utilization"]
    trends = []
    for m in metrics:
        trend = await cross_tenant_intelligence.analyze_enterprise_operational_trends(
            m, timeframe
        )
        d = trend.model_dump()
        # Map fields for frontend compatibility
        d["direction"] = "up" if trend.trend_direction == "increasing" else "down" if trend.trend_direction == "decreasing" else "stable"
        d["significance"] = "high" if trend.statistical_significance > 0.7 else "medium" if trend.statistical_significance > 0.4 else "low"
        trends.append(d)
    
    # If a specific metric was requested, return a single object (for backward compatibility if needed)
    # else return the list of trends as expected by the frontend.
    if metric:
        return {"success": True, "data": trends[0]}
    return {"success": True, "data": trends, "count": len(trends)}


@router.get("/tenant-benchmarks")
async def get_tenant_benchmarks(
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> dict:
    benchmarks = await cross_tenant_intelligence.get_tenant_operational_benchmarks(tenant_id)
    return {"success": True, "data": benchmarks}
