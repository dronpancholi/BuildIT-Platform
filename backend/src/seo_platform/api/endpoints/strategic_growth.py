from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.strategic_growth import strategic_growth

router = APIRouter()


@router.get("/strategic-growth/market-opportunities")
async def get_market_opportunities(tenant_id: UUID = Query(...)) -> dict:
    opportunities = await strategic_growth.detect_market_opportunities(tenant_id)
    return {
        "success": True,
        "data": [o.model_dump() for o in opportunities],
        "count": len(opportunities),
    }


@router.get("/strategic-growth/campaign-expansions")
async def get_campaign_expansions(tenant_id: UUID = Query(...)) -> dict:
    expansions = await strategic_growth.suggest_campaign_expansions(tenant_id)
    return {
        "success": True,
        "data": [e.model_dump() for e in expansions],
        "count": len(expansions),
    }


@router.get("/strategic-growth/keyword-opportunities")
async def get_keyword_opportunities(tenant_id: UUID = Query(...)) -> dict:
    opportunities = await strategic_growth.analyze_keyword_opportunities(tenant_id)
    return {
        "success": True,
        "data": [o.model_dump() for o in opportunities],
        "count": len(opportunities),
    }


@router.get("/strategic-growth/competitive-gaps")
async def get_competitive_gaps(tenant_id: UUID = Query(...)) -> dict:
    gaps = await strategic_growth.analyze_competitive_gaps(tenant_id)
    return {
        "success": True,
        "data": [g.model_dump() for g in gaps],
        "count": len(gaps),
    }


@router.get("/strategic-growth/growth-experiments")
async def get_growth_experiments(tenant_id: UUID = Query(...)) -> dict:
    experiments = await strategic_growth.suggest_growth_experiments(tenant_id)
    return {
        "success": True,
        "data": [e.model_dump() for e in experiments],
        "count": len(experiments),
    }


@router.get("/strategic-growth/resource-allocation")
async def get_resource_allocation(tenant_id: UUID = Query(...)) -> dict:
    suggestions = await strategic_growth.optimize_resource_allocation(tenant_id)
    return {
        "success": True,
        "data": [s.model_dump() for s in suggestions],
        "count": len(suggestions),
    }


@router.get("/strategic-growth/report")
async def get_strategic_growth_report(tenant_id: UUID = Query(...)) -> dict:
    report = await strategic_growth.generate_strategic_growth_report(tenant_id)
    return {"success": True, "data": report.model_dump()}
