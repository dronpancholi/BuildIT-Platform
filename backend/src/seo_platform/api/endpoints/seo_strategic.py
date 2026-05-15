"""
SEO Platform — Advanced SEO Strategic Intelligence Endpoints
===============================================================
REST endpoints exposing strategic keyword expansion, authority forecasting,
SERP trend forecasting, ranking opportunity prediction, local SEO expansion,
competitor dominance analysis, and topical authority propagation modeling.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, HTTPException, Query

from seo_platform.services.seo_strategic_intelligence import seo_strategic_intelligence

router = APIRouter()


@router.post("/keywords")
async def recommend_strategic_keywords(payload: dict) -> dict:
    """Recommend strategic keyword additions based on topical gaps."""
    tenant_id = payload.get("tenant_id")
    client_id = payload.get("client_id")
    if not tenant_id or not client_id:
        raise HTTPException(status_code=400, detail="tenant_id and client_id are required")
    try:
        recommendations = await seo_strategic_intelligence.recommend_strategic_keywords(
            tenant_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            client_id=UUID(client_id) if isinstance(client_id, str) else client_id,
        )
        return {"success": True, "data": [r.model_dump() for r in recommendations]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/authority-forecast")
async def get_authority_forecast(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    client_id: UUID = Query(..., description="Client UUID"),
    months: int = Query(6, ge=1, le=24, description="Forecast horizon in months"),
) -> dict:
    """Forecast semantic/topical authority growth over a period."""
    try:
        forecast = await seo_strategic_intelligence.forecast_semantic_authority(
            tenant_id=tenant_id,
            client_id=client_id,
            months=months,
        )
        return {"success": True, "data": forecast.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/serp-trends")
async def get_serp_trends(
    keyword: str = Query(..., min_length=1, description="Target keyword"),
    geo: str = Query("US", max_length=10, description="Geo target (country code)"),
    weeks: int = Query(12, ge=4, le=52, description="Forecast horizon in weeks"),
) -> dict:
    """Forecast SERP changes including feature prevalence and competitor patterns."""
    try:
        forecast = await seo_strategic_intelligence.forecast_serp_trends(
            keyword=keyword,
            geo=geo,
            weeks=weeks,
        )
        return {"success": True, "data": forecast.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ranking-opportunity")
async def predict_ranking_opportunity(payload: dict) -> dict:
    """Predict ability to rank for a keyword."""
    tenant_id = payload.get("tenant_id")
    keyword = payload.get("keyword", "")
    geo = payload.get("geo", "US")
    if not tenant_id or not keyword:
        raise HTTPException(status_code=400, detail="tenant_id and keyword are required")
    try:
        result = await seo_strategic_intelligence.predict_ranking_opportunity(
            tenant_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            keyword=keyword,
            geo=geo,
        )
        return {"success": True, "data": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/local-expansion")
async def recommend_local_seo_expansion(payload: dict) -> dict:
    """Recommend local SEO expansion into nearby cities/neighborhoods."""
    business_profile = payload.get("business_profile", {})
    if not business_profile:
        raise HTTPException(status_code=400, detail="business_profile is required")
    radius_miles = payload.get("radius_miles", 50)
    try:
        plan = await seo_strategic_intelligence.recommend_local_seo_expansion(
            business_profile=business_profile,
            radius_miles=radius_miles,
        )
        return {"success": True, "data": plan.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitor-dominance")
async def analyze_competitor_seo_dominance(payload: dict) -> dict:
    """Analyze competitor SEO dominance across multiple dimensions."""
    tenant_id = payload.get("tenant_id")
    client_id = payload.get("client_id")
    competitors = payload.get("competitors", [])
    if not tenant_id or not client_id or not competitors:
        raise HTTPException(status_code=400, detail="tenant_id, client_id, and competitors are required")
    try:
        report = await seo_strategic_intelligence.analyze_competitor_seo_dominance(
            tenant_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            client_id=UUID(client_id) if isinstance(client_id, str) else client_id,
            competitors=competitors,
        )
        return {"success": True, "data": report.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/authority-propagation")
async def model_topical_authority_propagation(payload: dict) -> dict:
    """Model how topical authority can propagate from dominant to adjacent topics."""
    tenant_id = payload.get("tenant_id")
    client_id = payload.get("client_id")
    if not tenant_id or not client_id:
        raise HTTPException(status_code=400, detail="tenant_id and client_id are required")
    try:
        model = await seo_strategic_intelligence.model_topical_authority_propagation(
            tenant_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
            client_id=UUID(client_id) if isinstance(client_id, str) else client_id,
        )
        return {"success": True, "data": model.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
