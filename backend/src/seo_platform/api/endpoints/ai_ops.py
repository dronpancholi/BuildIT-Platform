from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Query

from seo_platform.services.ai_operationalization import ai_operationalization

router = APIRouter()


@router.get("/ai-ops/inference-analytics")
async def get_inference_analytics(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    analytics = await ai_operationalization.get_inference_analytics(time_window_hours)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/ai-ops/prompt-performance")
async def get_prompt_performance() -> dict:
    results = await ai_operationalization.analyze_prompt_performance()
    return {
        "success": True,
        "data": [r.model_dump() for r in results],
        "count": len(results),
    }


@router.post("/ai-ops/detect-hallucinations")
async def detect_hallucinations(
    tenant_id: UUID = Body(..., embed=True),
) -> dict:
    result = await ai_operationalization.detect_hallucinations(tenant_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/ai-ops/confidence-drift")
async def get_confidence_drift(
    time_window_hours: int = Query(48, description="Time window in hours"),
) -> dict:
    alerts = await ai_operationalization.detect_confidence_drift(time_window_hours)
    return {
        "success": True,
        "data": [a.model_dump() for a in alerts],
        "count": len(alerts),
    }


@router.get("/ai-ops/operational-metrics")
async def get_operational_metrics() -> dict:
    metrics = await ai_operationalization.get_operational_metrics()
    return {"success": True, "data": metrics.model_dump()}
