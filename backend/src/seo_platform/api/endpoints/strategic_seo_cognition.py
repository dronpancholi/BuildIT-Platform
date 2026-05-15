from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Query

from seo_platform.services.strategic_seo_cognition import strategic_seo_cognition

router = APIRouter()


@router.get("/strategic-seo/authority-forecast")
async def get_authority_forecast(
    domain: str = Query(..., description="Domain to forecast"),
    months: int = Query(12, ge=1, le=60, description="Forecast period in months"),
) -> dict:
    forecast = await strategic_seo_cognition.forecast_authority(domain, months)
    return {"success": True, "data": forecast.model_dump()}


@router.get("/strategic-seo/backlink-ecosystem")
async def get_backlink_ecosystem(
    domain: str = Query(..., description="Domain to analyze"),
) -> dict:
    intelligence = await strategic_seo_cognition.analyze_backlink_ecosystem(domain)
    return {"success": True, "data": intelligence.model_dump()}


@router.get("/strategic-seo/serp-trend-forecast")
async def get_serp_trend_forecast(
    keyword: str = Query(..., description="Keyword to forecast"),
) -> dict:
    forecast = await strategic_seo_cognition.forecast_serp_trend(keyword)
    return {"success": True, "data": forecast.model_dump()}


@router.post("/strategic-seo/semantic-market-intelligence")
async def get_semantic_market_intelligence(
    market_segment: str = Body(..., description="Market segment to analyze"),
) -> dict:
    intelligence = await strategic_seo_cognition.analyze_semantic_market_intelligence(market_segment)
    return {"success": True, "data": intelligence.model_dump()}


@router.post("/strategic-seo/ranking-prediction")
async def get_ranking_prediction(
    keyword: str = Body(..., description="Target keyword"),
    campaign_id: str = Body(..., description="Campaign identifier"),
) -> dict:
    prediction = await strategic_seo_cognition.predict_long_term_ranking(keyword, campaign_id)
    return {"success": True, "data": prediction.model_dump()}


@router.get("/strategic-seo/operational-seo-strategy")
async def get_operational_seo_strategy(
    tenant_id: UUID = Query(..., description="Tenant ID"),
) -> dict:
    strategy = await strategic_seo_cognition.generate_operational_seo_strategy(tenant_id)
    return {"success": True, "data": strategy.model_dump()}


@router.post("/strategic-seo/authority-propagation-simulation")
async def get_authority_propagation_simulation(
    source_domain: str = Body(..., description="Source domain"),
    target_domain: str = Body(..., description="Target domain"),
) -> dict:
    simulation = await strategic_seo_cognition.simulate_authority_propagation(source_domain, target_domain)
    return {"success": True, "data": simulation.model_dump()}


@router.get("/strategic-seo/semantic-competitive-intelligence")
async def get_semantic_competitive_intelligence(
    competitor_domain: str = Query(..., description="Competitor domain"),
) -> dict:
    intelligence = await strategic_seo_cognition.analyze_semantic_competitive_intelligence(competitor_domain)
    return {"success": True, "data": intelligence.model_dump()}


@router.post("/strategic-seo/strategic-backlink-map")
async def get_strategic_backlink_map(
    target_domain: str = Body(..., description="Target domain for backlink map"),
) -> dict:
    backlink_map = await strategic_seo_cognition.build_strategic_backlink_map(target_domain)
    return {"success": True, "data": backlink_map.model_dump()}
