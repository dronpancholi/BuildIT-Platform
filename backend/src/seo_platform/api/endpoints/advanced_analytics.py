from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.advanced_analytics import advanced_analytics

router = APIRouter()


@router.get("/analytics/backlink-roi")
async def get_backlink_roi(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    campaign_id: UUID = Query(..., description="Campaign UUID"),
) -> dict:
    result = await advanced_analytics.analyze_backlink_roi(tenant_id, campaign_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/analytics/campaign-efficiency")
async def get_campaign_efficiency(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
) -> dict:
    results = await advanced_analytics.analyze_campaign_efficiency(tenant_id)
    return {"success": True, "data": [r.model_dump() for r in results]}


@router.get("/analytics/workflow-latency")
async def get_workflow_latency(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    results = await advanced_analytics.analyze_workflow_latency(tenant_id, time_window_hours)
    return {"success": True, "data": [r.model_dump() for r in results]}


@router.get("/analytics/scraping-quality")
async def get_scraping_quality(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    results = await advanced_analytics.analyze_scraping_quality(time_window_hours)
    return {"success": True, "data": [r.model_dump() for r in results]}


@router.get("/analytics/outreach-performance")
async def get_outreach_performance(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    time_window_hours: int = Query(168, description="Time window in hours"),
) -> dict:
    results = await advanced_analytics.analyze_outreach_performance(tenant_id, time_window_hours)
    return {"success": True, "data": [r.model_dump() for r in results]}


@router.get("/analytics/local-seo-effectiveness")
async def get_local_seo_effectiveness(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    time_window_days: int = Query(30, description="Time window in days"),
) -> dict:
    result = await advanced_analytics.analyze_local_seo_effectiveness(tenant_id, time_window_days)
    return {"success": True, "data": result.model_dump()}
