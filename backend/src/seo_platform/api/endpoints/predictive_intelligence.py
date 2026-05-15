from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

from seo_platform.services.predictive_intelligence import predictive_intelligence

router = APIRouter()


class WorkflowFailureRequest(BaseModel):
    workflow_id: str


class CampaignForecastRequest(BaseModel):
    campaign_id: UUID


class BacklinkAcquisitionRequest(BaseModel):
    tenant_id: UUID
    prospect_domain: str


@router.post("/workflow-failure")
async def predict_workflow_failure(request: WorkflowFailureRequest) -> dict:
    prediction = await predictive_intelligence.predict_workflow_failure(
        request.workflow_id,
    )
    return {"success": True, "data": prediction.model_dump()}


@router.get("/queue-saturation")
async def predict_queue_saturation(
    queue_name: str = Query(...),
    lookahead_minutes: int = Query(30, ge=5, le=120),
) -> dict:
    prediction = await predictive_intelligence.predict_queue_saturation(
        queue_name, lookahead_minutes,
    )
    return {"success": True, "data": prediction.model_dump()}


@router.get("/scraping-degradation")
async def predict_scraping_degradation(
    engine_name: str = Query(...),
    lookahead_hours: int = Query(2, ge=1, le=24),
) -> dict:
    prediction = await predictive_intelligence.predict_scraping_degradation(
        engine_name, lookahead_hours,
    )
    return {"success": True, "data": prediction.model_dump()}


@router.get("/ai-confidence")
async def predict_ai_confidence_degradation(
    task_type: str = Query(...),
    lookahead_hours: int = Query(4, ge=1, le=48),
) -> dict:
    prediction = await predictive_intelligence.predict_ai_confidence_degradation(
        task_type, lookahead_hours,
    )
    return {"success": True, "data": prediction.model_dump()}


@router.get("/communication-failure")
async def predict_communication_failure(
    tenant_id: UUID = Query(...),
    campaign_id: UUID = Query(...),
) -> dict:
    prediction = await predictive_intelligence.predict_communication_failure(
        tenant_id, campaign_id,
    )
    return {"success": True, "data": prediction.model_dump()}


@router.get("/infrastructure-bottlenecks")
async def predict_infrastructure_bottlenecks(
    lookahead_hours: int = Query(2, ge=1, le=24),
) -> dict:
    predictions = await predictive_intelligence.predict_infrastructure_bottlenecks(
        lookahead_hours,
    )
    return {
        "success": True,
        "data": [p.model_dump() for p in predictions],
        "count": len(predictions),
    }


@router.post("/campaign-forecast")
async def forecast_campaign_performance(request: CampaignForecastRequest) -> dict:
    forecast = await predictive_intelligence.forecast_campaign_performance(
        request.campaign_id,
    )
    return {"success": True, "data": forecast.model_dump()}


@router.post("/backlink-acquisition")
async def predict_backlink_acquisition(request: BacklinkAcquisitionRequest) -> dict:
    prediction = await predictive_intelligence.predict_backlink_acquisition(
        request.tenant_id, request.prospect_domain,
    )
    return {"success": True, "data": prediction.model_dump()}
