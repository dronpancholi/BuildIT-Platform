"""
SEO Platform — Outreach Optimization Intelligence Endpoints
============================================================
REST endpoints exposing response prediction, subject-line analysis,
timing optimization, prospect prioritization, communication scoring,
follow-up intelligence, and relationship depth scoring.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from seo_platform.services.outreach_intelligence import outreach_intelligence

router = APIRouter()


@router.post("/predict-response")
async def predict_response(outreach_data: dict) -> dict:
    """Predict likelihood of response for an outreach."""
    prediction = outreach_intelligence.predict_response_likelihood(outreach_data)
    return {"success": True, "data": prediction}


@router.post("/analyze-subject")
async def analyze_subject(payload: dict) -> dict:
    """Analyze subject line effectiveness."""
    subject = payload.get("subject", "")
    prospect_data = payload.get("prospect_data", {})
    analysis = outreach_intelligence.analyze_subject_line(subject, prospect_data)
    return {"success": True, "data": analysis}


@router.post("/timing")
async def recommend_timing(prospect_data: dict) -> dict:
    """Recommend optimal outreach timing."""
    timing = outreach_intelligence.recommend_outreach_timing(prospect_data)
    return {"success": True, "data": timing}


@router.post("/prioritize")
async def prioritize_prospects(payload: dict) -> dict:
    """Rank prospects by composite priority score."""
    prospects = payload.get("prospects", [])
    campaign_context = payload.get("campaign_context", {})
    if not prospects:
        raise HTTPException(status_code=400, detail="prospects list is required")
    prioritized = outreach_intelligence.prioritize_prospects(prospects, campaign_context)
    return {"success": True, "data": prioritized}


@router.post("/score-communication")
async def score_communication(payload: dict) -> dict:
    """Score email communication quality."""
    email_content = payload.get("email_content", "")
    if not email_content:
        raise HTTPException(status_code=400, detail="email_content is required")
    score = outreach_intelligence.score_communication_quality(email_content)
    return {"success": True, "data": score}


@router.post("/follow-up")
async def recommend_follow_up(email_thread: dict) -> dict:
    """Recommend follow-up strategy for an email thread."""
    try:
        recommendation = await outreach_intelligence.recommend_follow_up(email_thread)
        return {"success": True, "data": recommendation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationship-depth")
async def get_relationship_depth(
    tenant_id: UUID,
    domain: str = Query(..., description="Domain to score relationship depth for"),
) -> dict:
    """Score ongoing relationship depth with a domain."""
    try:
        depth = await outreach_intelligence.score_relationship_depth(tenant_id, domain)
        return {"success": True, "data": depth}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
