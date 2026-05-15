from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Query

from seo_platform.services.ai_quality import ai_quality_service

router = APIRouter()


@router.post("/ai-quality/recommendation-confidence")
async def score_recommendation_confidence(
    recommendation_type: str = Body(..., embed=True),
    signals: dict[str, Any] = Body(..., embed=True),
) -> dict:
    result = await ai_quality_service.score_recommendation_confidence(recommendation_type, signals)
    return {"success": True, "data": result.model_dump()}


@router.post("/ai-quality/hallucination-risk")
async def score_hallucination_risk(
    llm_output: str = Body(..., embed=True),
    validation_context: dict[str, Any] = Body(..., embed=True),
) -> dict:
    result = await ai_quality_service.score_hallucination_risk(llm_output, validation_context)
    return {"success": True, "data": result.model_dump()}


@router.get("/ai-quality/recommendation-quality")
async def get_recommendation_quality(
    time_window_hours: int = Query(168, description="Time window in hours"),
) -> dict:
    result = await ai_quality_service.analyze_recommendation_quality(time_window_hours)
    return {"success": True, "data": result.model_dump()}


@router.post("/ai-quality/clustering-quality")
async def score_clustering_quality(
    clusters: list[dict[str, Any]] = Body(..., embed=True),
) -> dict:
    result = await ai_quality_service.score_clustering_quality(clusters)
    return {"success": True, "data": result.model_dump()}


@router.post("/ai-quality/outreach-quality")
async def score_outreach_quality(
    email_content: str = Body(..., embed=True),
    prospect_data: dict[str, Any] = Body(..., embed=True),
) -> dict:
    result = await ai_quality_service.score_outreach_quality(email_content, prospect_data)
    return {"success": True, "data": result.model_dump()}


@router.get("/ai-quality/dashboard")
async def get_ai_quality_dashboard(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
) -> dict:
    result = await ai_quality_service.get_ai_quality_dashboard(tenant_id)
    return {"success": True, "data": result.model_dump()}
