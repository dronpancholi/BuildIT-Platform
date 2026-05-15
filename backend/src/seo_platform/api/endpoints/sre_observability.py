"""
SEO Platform — SRE Observability REST Endpoints
==================================================
SRE-grade monitoring endpoints: traces, topology, queue pressure,
heatmaps, worker saturation, replay/scraping/AI analytics,
event propagation, anomaly heatmaps, incident dashboard, trace replay.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Query

from seo_platform.services.sre_observability import sre_observability

router = APIRouter()


@router.get("/sre/traces")
async def get_distributed_traces(
    tenant_id: str | None = Query(None, description="Filter by tenant UUID"),
    workflow_type: str | None = Query(None, description="Filter by workflow type"),
    status: str | None = Query(None, description="Filter by execution status"),
    time_window_hours: int = Query(24, description="Time window in hours"),
):
    """Return full distributed trace context with activity spans."""
    filters = {
        "tenant_id": tenant_id,
        "workflow_type": workflow_type,
        "status": status,
        "time_window_hours": time_window_hours,
    }
    traces = await sre_observability.get_distributed_traces(filters)
    return {
        "success": True,
        "data": [t.model_dump() for t in traces],
        "count": len(traces),
    }


@router.get("/sre/topology")
async def get_infra_topology():
    """Return current infrastructure topology with nodes, edges, and dependency health."""
    topology = await sre_observability.get_infra_topology()
    return {"success": True, "data": topology.model_dump()}


@router.get("/sre/queue-pressure")
async def get_queue_pressure_dashboard():
    """Return per-queue pressure analysis with thresholds, trends, and scores."""
    dashboard = await sre_observability.get_queue_pressure_dashboard()
    return {"success": True, "data": dashboard.model_dump()}


@router.get("/sre/queue-heatmap")
async def get_queue_heatmap(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """Return queue depth time series data for heatmap visualization."""
    heatmap_data = await sre_observability.get_queue_heatmap_data(hours=hours)
    return {
        "success": True,
        "data": [h.model_dump() for h in heatmap_data],
        "count": len(heatmap_data),
    }


@router.get("/sre/workflow-heatmap")
async def get_workflow_heatmap(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """Return workflow execution heatmap: starts, completions, failures, duration per hour."""
    heatmap = await sre_observability.get_workflow_heatmap_data(hours=hours)
    return {"success": True, "data": heatmap.model_dump()}


@router.get("/sre/worker-saturation")
async def get_worker_saturation():
    """Return per-worker utilization: active tasks, slot %, task duration, health check."""
    saturation = await sre_observability.get_worker_saturation()
    return {
        "success": True,
        "data": [s.model_dump() for s in saturation],
        "count": len(saturation),
    }


@router.get("/sre/replay-analytics")
async def get_replay_analytics(
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """Return replay safety analytics: types, success rate, non-determinism errors."""
    analytics = await sre_observability.get_replay_analytics(
        time_window_hours=time_window_hours,
    )
    return {"success": True, "data": analytics.model_dump()}


@router.get("/sre/scraping-latency")
async def get_scraping_latency(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """Return scraping latency analytics: P50/P95/P99, cache hit rate, error rate."""
    analytics = await sre_observability.get_scraping_latency_analytics(hours=hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/sre/ai-latency")
async def get_ai_latency(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """Return AI inference latency analytics: model breakdown, tokens/s, queue wait, fallbacks."""
    analytics = await sre_observability.get_ai_latency_analytics(hours=hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/sre/event-propagation")
async def get_event_propagation_telemetry(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """Return end-to-end event propagation timing per event type."""
    telemetry = await sre_observability.get_event_propagation_telemetry(hours=hours)
    return {"success": True, "data": telemetry.model_dump()}


@router.get("/sre/anomaly-heatmap")
async def get_anomaly_heatmap(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """Return anomaly frequency heatmap per type per hour."""
    heatmap = await sre_observability.get_anomaly_heatmap_data(hours=hours)
    return {"success": True, "data": heatmap.model_dump()}


@router.get("/sre/incident-dashboard")
async def get_incident_dashboard():
    """Return active and recent incidents with MTTD and MTTR."""
    dashboard = await sre_observability.get_incident_dashboard()
    return {"success": True, "data": dashboard.model_dump()}


@router.post("/sre/replay-trace")
async def replay_trace(
    trace_id: str = Body(..., embed=True, description="Workflow trace ID to replay"),
):
    """Replay a distributed trace, reconstructing the full execution path."""
    result = await sre_observability.replay_trace(trace_id=trace_id)
    return {"success": result.success, "data": result.model_dump()}
