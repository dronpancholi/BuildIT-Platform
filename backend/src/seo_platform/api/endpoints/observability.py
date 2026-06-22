"""
SEO Platform — Enterprise Observability Endpoints
====================================================
REST endpoints for distributed tracing, workflow analytics, retry analytics,
AI inference analytics, scraping telemetry, and communication telemetry.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, Query

from seo_platform.services.observability_service import observability_service

router = APIRouter()


@router.get("/traces")
async def get_traces(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    workflow_type: str | None = Query(None, description="Filter by workflow type"),
    status: str | None = Query(None, description="Filter by execution status"),
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    """Return distributed traces with per-activity timing spans."""
    filters = {
        "workflow_type": workflow_type,
        "status": status,
        "time_window_hours": time_window_hours,
    }
    traces = await observability_service.get_traces(tenant_id, filters)
    return {
        "success": True,
        "data": [t.model_dump() for t in traces],
        "count": len(traces),
    }


@router.get("/workflow-analytics")
async def get_workflow_analytics(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    """Return aggregated workflow execution metrics."""
    analytics = await observability_service.get_workflow_analytics(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/retry-analytics")
async def get_retry_analytics(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    """Return retry analytics per activity type."""
    analytics = await observability_service.get_retry_analytics(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/inference-analytics")
async def get_inference_analytics(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    """Return AI inference analytics from Prometheus / Redis."""
    analytics = await observability_service.get_ai_inference_analytics(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/scraping-telemetry")
async def get_scraping_telemetry(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    """Return scraping telemetry from Redis."""
    telemetry = await observability_service.get_scraping_telemetry(time_window_hours)
    return {"success": True, "data": telemetry.model_dump()}


@router.get("/communication-telemetry")
async def get_communication_telemetry(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    """Return email communication telemetry from database."""
    telemetry = await observability_service.get_communication_telemetry(
        tenant_id, time_window_hours
    )
    return {"success": True, "data": telemetry.model_dump()}
