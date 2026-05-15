from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

from seo_platform.services.adaptive_optimization import adaptive_optimization

router = APIRouter()


@router.get("/adaptive-optimization/queue-prioritization")
async def suggest_queue_prioritization() -> dict:
    suggestions = await adaptive_optimization.suggest_queue_prioritization()
    return {
        "success": True,
        "data": [s.model_dump() for s in suggestions],
        "count": len(suggestions),
    }


@router.get("/adaptive-optimization/retry-tuning")
async def get_retry_tuning(
    activity_type: str | None = Query(None),
) -> dict:
    if activity_type:
        suggestion = await adaptive_optimization.suggest_retry_tuning(activity_type)
        return {"success": True, "data": suggestion.model_dump()}
    else:
        report = await adaptive_optimization.get_retry_optimization_report()
        return {"success": True, "data": report.model_dump()}


@router.get("/adaptive-optimization/workflow")
async def suggest_workflow_optimization(
    workflow_type: str = Query(...),
) -> dict:
    suggestion = await adaptive_optimization.suggest_workflow_optimization(
        workflow_type,
    )
    return {"success": True, "data": suggestion.model_dump()}


@router.get("/adaptive-optimization/scraping")
async def suggest_scraping_optimization() -> dict:
    suggestion = await adaptive_optimization.suggest_scraping_optimization()
    return {"success": True, "data": suggestion.model_dump()}


@router.get("/adaptive-optimization/worker-allocation")
async def suggest_worker_allocation() -> dict:
    suggestions = await adaptive_optimization.suggest_worker_allocation()
    return {
        "success": True,
        "data": [s.model_dump() for s in suggestions],
        "count": len(suggestions),
    }


@router.get("/adaptive-optimization/event-propagation")
async def suggest_event_propagation_tuning() -> dict:
    suggestion = await adaptive_optimization.suggest_event_propagation_tuning()
    return {"success": True, "data": suggestion.model_dump()}


@router.get("/adaptive-optimization/communication-timing")
async def suggest_communication_timing(
    tenant_id: UUID = Query(...),
    campaign_id: UUID = Query(...),
) -> dict:
    suggestion = await adaptive_optimization.suggest_communication_timing(
        tenant_id, campaign_id,
    )
    return {"success": True, "data": suggestion.model_dump()}
