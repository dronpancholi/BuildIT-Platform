"""
SEO Platform — Advanced Backlink Acquisition Intelligence Endpoints
======================================================================
REST endpoints exposing backlink opportunity prediction, relationship network
analysis, warm introduction suggestions, authority propagation paths,
outreach success forecasting, prospect intent analysis, and campaign
optimization intelligence.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions.
"""

from __future__ import annotations

from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, HTTPException, Query

from seo_platform.services.backlink_acquisition_intelligence import (
    backlink_acquisition_intelligence,
)

router = APIRouter()


@router.get("/opportunities")
async def predict_backlink_opportunities(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    campaign_id: UUID = Query(..., description="Campaign UUID"),
) -> dict:
    """Predict best backlink opportunities from prospect graph, broken links, and content gaps."""
    try:
        opportunities = await backlink_acquisition_intelligence.predict_backlink_opportunities(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
        return {"success": True, "data": [o.model_dump() for o in opportunities]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationship-network")
async def analyze_relationship_network(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    campaign_id: UUID = Query(..., description="Campaign UUID"),
) -> dict:
    """Analyze prospect relationship network for connections, clusters, and centrality."""
    try:
        network = await backlink_acquisition_intelligence.analyze_relationship_network(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
        return {"success": True, "data": network.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/introductions")
async def recommend_introductions(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    campaign_id: UUID = Query(..., description="Campaign UUID"),
) -> dict:
    """Suggest warm introduction opportunities from prospect relationships."""
    try:
        suggestions = await backlink_acquisition_intelligence.recommend_introductions(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
        return {"success": True, "data": [s.model_dump() for s in suggestions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/authority-propagation")
async def analyze_authority_propagation_paths(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    domain: str = Query(..., min_length=1, description="Domain to analyze"),
) -> dict:
    """Map authority flow through the network to identify high-value additions."""
    try:
        path = await backlink_acquisition_intelligence.analyze_authority_propagation_paths(
            tenant_id=tenant_id,
            domain=domain,
        )
        return {"success": True, "data": path.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outreach-forecast")
async def forecast_outreach_success(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    campaign_id: UUID = Query(..., description="Campaign UUID"),
    weeks: int = Query(4, ge=1, le=12, description="Forecast horizon in weeks"),
) -> dict:
    """Forecast outreach outcomes including expected replies, responses, and links."""
    try:
        forecast = await backlink_acquisition_intelligence.forecast_outreach_success(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            weeks=weeks,
        )
        return {"success": True, "data": forecast.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prospect-intent")
async def analyze_prospect_intent(payload: dict) -> dict:
    """Classify a prospect domain's likely intent for backlink acquisition."""
    prospect_domain = payload.get("prospect_domain", "")
    if not prospect_domain:
        raise HTTPException(status_code=400, detail="prospect_domain is required")
    try:
        intent = await backlink_acquisition_intelligence.analyze_prospect_intent(
            prospect_domain=prospect_domain,
        )
        return {"success": True, "data": intent.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaign-optimization")
async def analyze_campaign_optimization(
    tenant_id: UUID = Query(..., description="Tenant UUID"),
    campaign_id: UUID = Query(..., description="Campaign UUID"),
) -> dict:
    """Comprehensive campaign optimization analysis across multiple dimensions."""
    try:
        analysis = await backlink_acquisition_intelligence.analyze_campaign_optimization(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
        return {"success": True, "data": analysis.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
