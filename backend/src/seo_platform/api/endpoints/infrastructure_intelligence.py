"""
SEO Platform — Infrastructure Intelligence Endpoints
=======================================================
REST endpoints for infrastructure topology, queue saturation, worker utilization,
orchestration bottlenecks, and LLM-generated infrastructure insights.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from fastapi import APIRouter, Query

from seo_platform.services.infrastructure_intelligence import infrastructure_intelligence

router = APIRouter()


@router.get("/topology")
async def get_topology() -> dict:
    """Return infrastructure topology dependency graph."""
    topology = await infrastructure_intelligence.analyze_topology()
    return {"success": True, "data": topology.model_dump()}


@router.get("/queue-saturation")
async def get_queue_saturation() -> dict:
    """Return queue saturation analysis with z-score anomaly detection."""
    saturation = await infrastructure_intelligence.detect_queue_saturation()
    return {
        "success": True,
        "data": [s.model_dump() for s in saturation],
    }


@router.get("/worker-utilization")
async def get_worker_utilization() -> dict:
    """Return worker utilization analysis."""
    utilization = await infrastructure_intelligence.analyze_worker_utilization()
    return {"success": True, "data": utilization.model_dump()}


@router.get("/bottlenecks")
async def get_bottlenecks(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    """Return orchestration bottleneck analysis."""
    bottlenecks = await infrastructure_intelligence.analyze_orchestration_bottlenecks(
        time_window_hours
    )
    return {"success": True, "data": bottlenecks.model_dump()}


@router.get("/insights")
async def get_infrastructure_insights() -> dict:
    """Return LLM-generated infrastructure health insights (advisory only)."""
    insights = await infrastructure_intelligence.generate_infrastructure_insights()
    return {"success": True, "data": insights.model_dump()}
