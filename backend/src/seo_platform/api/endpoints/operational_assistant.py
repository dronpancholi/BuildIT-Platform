from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Body
from pydantic import BaseModel

from seo_platform.services.operational_assistant import operational_assistant

router = APIRouter()


class ExplainAnomalyRequest(BaseModel):
    anomaly_type: str
    anomaly_data: dict[str, Any]


@router.get("/workflow")
async def get_workflow_assistance(tenant_id: UUID = Query(...)) -> dict:
    recommendations = await operational_assistant.get_workflow_assistance(tenant_id)
    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
    }


@router.get("/campaign")
async def get_campaign_assistance(
    tenant_id: UUID = Query(...),
    campaign_id: UUID | None = Query(None),
) -> dict:
    recommendations = await operational_assistant.get_campaign_assistance(
        tenant_id, campaign_id,
    )
    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
    }


@router.post("/explain-anomaly")
async def explain_anomaly(request: ExplainAnomalyRequest) -> dict:
    explanation = await operational_assistant.explain_anomaly(
        request.anomaly_type, request.anomaly_data,
    )
    return {"success": True, "data": explanation.model_dump()}


@router.get("/queue")
async def get_queue_assistance() -> dict:
    recommendations = await operational_assistant.get_queue_assistance()
    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
    }


@router.get("/scraping")
async def get_scraping_assistance() -> dict:
    recommendations = await operational_assistant.get_scraping_assistance()
    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
    }


@router.get("/infrastructure")
async def get_infrastructure_assistance() -> dict:
    recommendations = await operational_assistant.get_infrastructure_assistance()
    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
    }


@router.get("/prioritize")
async def prioritize_operational_actions(
    tenant_id: UUID = Query(...),
) -> dict:
    actions = await operational_assistant.prioritize_operational_actions(tenant_id)
    return {
        "success": True,
        "data": [a.model_dump() for a in actions],
        "count": len(actions),
    }
