"""
SEO Platform — Backlink Intelligence Endpoints
================================================
REST endpoints exposing prospect graph analysis, outreach success prediction,
response intelligence, and authority propagation analysis.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from seo_platform.services.backlink_engine.advanced_intelligence import advanced_backlink_intelligence
from seo_platform.services.backlink_engine.intelligence import backlink_intelligence

router = APIRouter()


@router.get("/prospect-graph/{campaign_id}")
async def get_prospect_graph(campaign_id: UUID) -> dict:
    """Return prospect relationship graph for a campaign."""
    try:
        graph = await backlink_intelligence.build_prospect_graph(campaign_id)
        return {"success": True, "data": graph}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict-success")
async def predict_outreach_success(prospect_data: dict) -> dict:
    """Predict outreach success probability for a prospect."""
    prediction = backlink_intelligence.predict_outreach_success(prospect_data)
    return {"success": True, "data": prediction}


@router.post("/analyze-response")
async def analyze_outreach_response(email_thread: dict) -> dict:
    """Analyze an outreach email reply for sentiment and next actions."""
    analysis = await backlink_intelligence.analyze_outreach_response(email_thread)
    return {"success": True, "data": analysis}


@router.get("/authority-propagation")
async def get_authority_propagation(domain: str = Query(..., description="Domain to analyze")) -> dict:
    """Trace authority flow for a domain."""
    try:
        propagation = await backlink_intelligence.analyze_authority_propagation(domain)
        return {"success": True, "data": propagation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prospect-quality")
async def score_prospect_quality(payload: dict) -> dict:
    """Detailed prospect quality scoring with per-component breakdown."""
    prospect_data = payload.get("prospect_data", {})
    campaign_context = payload.get("campaign_context", {})
    score = advanced_backlink_intelligence.score_prospect_quality_detailed(
        prospect_data, campaign_context,
    )
    return {"success": True, "data": score}


@router.get("/authority-analysis")
async def analyze_backlink_authority(domain: str = Query(..., description="Domain to analyze")) -> dict:
    """Deep authority assessment for a domain."""
    try:
        analysis = await advanced_backlink_intelligence.analyze_backlink_authority(domain)
        return {"success": True, "data": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict-opportunity")
async def predict_opportunity(payload: dict) -> dict:
    """Predict backlink opportunity likelihood."""
    prospect_domain = payload.get("prospect_domain", "")
    target_domain = payload.get("target_domain", "")
    if not prospect_domain or not target_domain:
        raise HTTPException(status_code=400, detail="prospect_domain and target_domain are required")
    try:
        prediction = await advanced_backlink_intelligence.predict_backlink_opportunity(
            prospect_domain, target_domain,
        )
        return {"success": True, "data": prediction}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/response-probability")
async def analyze_response_probability(payload: dict) -> dict:
    """Analyze response probability for a prospect."""
    prospect_data = payload.get("prospect_data", {})
    campaign_type = payload.get("campaign_type", "guest_post")
    analysis = advanced_backlink_intelligence.analyze_response_probability(
        prospect_data, campaign_type,
    )
    return {"success": True, "data": analysis}
