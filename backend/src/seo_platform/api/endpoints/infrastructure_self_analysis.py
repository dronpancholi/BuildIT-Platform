"""
SEO Platform — Infrastructure Self-Analysis Endpoints
========================================================
REST endpoints for autonomous infrastructure analysis.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.infrastructure_self_analysis import infrastructure_self_analysis

router = APIRouter()


@router.get("/infra-self-analysis/topology")
async def get_topology_intelligence() -> dict:
    """Return intelligent infrastructure topology analysis with causal dependencies."""
    report = await infrastructure_self_analysis.analyze_infra_topology_intelligence()
    return {"success": True, "data": report.model_dump()}


@router.get("/infra-self-analysis/bottlenecks")
async def get_bottleneck_self_analysis() -> dict:
    """Return autonomous bottleneck detection and analysis."""
    bottlenecks = await infrastructure_self_analysis.self_analyze_bottlenecks()
    return {"success": True, "data": [b.model_dump() for b in bottlenecks]}


@router.get("/infra-self-analysis/workflow-congestion")
async def get_workflow_congestion() -> dict:
    """Return workflow-level congestion analysis."""
    report = await infrastructure_self_analysis.analyze_workflow_congestion()
    return {"success": True, "data": report.model_dump()}


@router.get("/infra-self-analysis/worker-imbalance")
async def get_worker_imbalance() -> dict:
    """Return worker allocation imbalance detection."""
    report = await infrastructure_self_analysis.detect_worker_imbalance()
    return {"success": True, "data": report.model_dump()}


@router.get("/infra-self-analysis/queue-health-forecast")
async def get_queue_health_forecast(
    lookahead_hours: int = Query(4, description="Hours to look ahead"),
) -> dict:
    """Return queue health forecast with predicted depths and risk levels."""
    forecast = await infrastructure_self_analysis.forecast_queue_health(lookahead_hours)
    return {"success": True, "data": forecast.model_dump()}


@router.get("/infra-self-analysis/degradation")
async def get_degradation_intelligence() -> dict:
    """Return advanced infrastructure degradation analysis."""
    report = await infrastructure_self_analysis.analyze_infra_degradation_intelligence()
    return {"success": True, "data": report.model_dump()}


@router.get("/infra-self-analysis/pressure")
async def get_operational_pressure() -> dict:
    """Return comprehensive operational pressure analysis."""
    report = await infrastructure_self_analysis.analyze_operational_pressure()
    return {"success": True, "data": report.model_dump()}
