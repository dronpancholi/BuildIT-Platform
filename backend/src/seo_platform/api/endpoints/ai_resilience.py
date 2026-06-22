from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, Query

from seo_platform.services.ai_resilience import ai_resilience

router = APIRouter()


@router.get("/fallback-route")
async def get_fallback_route(
    task_type: str = Query(..., description="Task type"),
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> dict:
    route = await ai_resilience.get_fallback_route(task_type, tenant_id)
    return {"success": True, "data": route.model_dump()}


@router.get("/inference-health")
async def get_inference_health(
    model_id: str = Query(..., description="Model ID"),
    time_window_hours: int = Query(1, description="Time window in hours"),
) -> dict:
    score = await ai_resilience.score_inference_health(model_id, time_window_hours)
    return {"success": True, "data": score.model_dump()}


@router.get("/failure-analytics")
async def get_failure_analytics(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    analytics = await ai_resilience.get_ai_failure_analytics(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/drift-detection")
async def get_drift_detection(
    time_window_hours: int = Query(48, description="Time window in hours"),
) -> dict:
    alerts = await ai_resilience.detect_confidence_drift_enhanced(time_window_hours)
    return {
        "success": True,
        "data": [a.model_dump() for a in alerts],
        "count": len(alerts),
    }


@router.get("/throttle-status")
async def get_throttle_status(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    task_type: str = Query(..., description="Task type"),
) -> dict:
    result = await ai_resilience.check_ai_operational_throttle(tenant_id, task_type)
    return {"success": True, "data": result.model_dump()}
