"""
SEO Platform — Infrastructure Economics Endpoints
====================================================
REST endpoints for analyzing real resource usage and costs.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.infrastructure_economics import infrastructure_economics

router = APIRouter()


@router.get("/infra-economics/ai-costs")
async def get_ai_costs(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return AI cost analytics including per-model and per-task costs."""
    analytics = await infrastructure_economics.analyze_ai_costs(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/infra-economics/queue-costs")
async def get_queue_costs(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return queue cost analytics with per-queue breakdown and idle cost estimation."""
    analytics = await infrastructure_economics.analyze_queue_costs(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/infra-economics/scraping-costs")
async def get_scraping_costs(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return scraping cost analytics with per-engine breakdown."""
    analytics = await infrastructure_economics.analyze_scraping_costs(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/infra-economics/utilization")
async def get_infra_utilization(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return infrastructure utilization analytics with under/over utilized resources."""
    analytics = await infrastructure_economics.analyze_infra_utilization(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/infra-economics/worker-efficiency")
async def get_worker_efficiency(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return worker efficiency analytics with cost breakdown and idle time."""
    analytics = await infrastructure_economics.analyze_worker_efficiency(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/infra-economics/event-throughput")
async def get_event_throughput(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return event throughput economics with per-topic cost analysis."""
    analytics = await infrastructure_economics.analyze_event_throughput_economics(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/infra-economics/roi")
async def get_operational_roi(
    tenant_id: str = Query(..., description="Tenant UUID"),
    time_window_days: int = Query(30, ge=1, le=365, description="Days to analyze"),
):
    """Return operational ROI calculation for a tenant."""
    tid = UUID(tenant_id)
    roi = await infrastructure_economics.calculate_operational_roi(tid, time_window_days)
    return {"success": True, "data": roi.model_dump()}


@router.get("/infra-economics/optimization-intelligence")
async def get_optimization_intelligence(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return comprehensive resource optimization recommendations."""
    intelligence = await infrastructure_economics.generate_resource_optimization_intelligence(time_window_hours)
    return {"success": True, "data": intelligence.model_dump()}


@router.get("/infra-economics/cost-optimization")
async def get_cost_optimization(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return infrastructure cost optimization opportunities and estimated savings."""
    optimization = await infrastructure_economics.optimize_infra_costs(time_window_hours)
    return {"success": True, "data": optimization.model_dump()}


@router.get("/infra-economics/ai-efficiency")
async def get_ai_efficiency(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return AI efficiency optimization with model usage breakdown and cost per token."""
    efficiency = await infrastructure_economics.optimize_ai_efficiency(time_window_hours)
    return {"success": True, "data": efficiency.model_dump()}


@router.get("/infra-economics/scraping-efficiency")
async def get_scraping_efficiency(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return scraping efficiency analytics with waste analysis and optimization opportunities."""
    analytics = await infrastructure_economics.analyze_scraping_efficiency(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/infra-economics/queue-efficiency")
async def get_queue_efficiency(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return queue efficiency intelligence with utilization and scaling optimizations."""
    intelligence = await infrastructure_economics.analyze_queue_efficiency(time_window_hours)
    return {"success": True, "data": intelligence.model_dump()}


@router.get("/infra-economics/worker-utilization")
async def get_worker_utilization(
    time_window_hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Return worker utilization optimization with rebalancing plan."""
    optimization = await infrastructure_economics.optimize_worker_utilization(time_window_hours)
    return {"success": True, "data": optimization.model_dump()}


@router.get("/infra-economics/roi-forecast")
async def get_roi_forecast(
    timeframe_days: int = Query(30, ge=1, le=365, description="Days to forecast"),
):
    """Return operational ROI forecast with projected costs, value, and confidence intervals."""
    forecast = await infrastructure_economics.forecast_operational_roi(timeframe_days)
    return {"success": True, "data": forecast.model_dump()}
