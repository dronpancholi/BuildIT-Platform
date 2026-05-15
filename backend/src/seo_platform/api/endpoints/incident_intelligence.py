"""
SEO Platform — Incident Intelligence Endpoints
================================================
REST endpoints for AI-assisted operational incident intelligence.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Query

from seo_platform.services.incident_intelligence import incident_intelligence

router = APIRouter()


@router.get("/incident-intelligence/predictions")
async def predict_incidents(
    lookahead_minutes: int = Query(60, ge=5, le=1440, description="Minutes to look ahead"),
) -> dict:
    """Predict likely incidents based on current system state."""
    predictions = await incident_intelligence.predict_incidents(
        lookahead_minutes=lookahead_minutes,
    )
    return {"success": True, "data": [p.model_dump() for p in predictions]}


@router.post("/incident-intelligence/cluster")
async def cluster_incidents(
    incidents: list[dict] = Body(..., description="Incidents to cluster"),
) -> dict:
    """Cluster related incidents by common patterns."""
    clusters = await incident_intelligence.cluster_incidents(
        incidents=incidents,
    )
    return {"success": True, "data": [c.model_dump() for c in clusters]}


@router.post("/incident-intelligence/severity-score")
async def score_incident_severity(
    incident_id: str = Body(..., description="Incident ID"),
    incident_data: dict = Body(..., description="Incident data for scoring"),
) -> dict:
    """Calculate severity score for an incident."""
    score = await incident_intelligence.score_incident_severity(
        incident_id=incident_id,
        incident_data=incident_data,
    )
    return {"success": True, "data": score.model_dump()}


@router.post("/incident-intelligence/analyze")
async def analyze_incident(
    incident_id: str = Body(..., description="Incident ID"),
    incident_data: dict = Body(..., description="Incident data for analysis"),
) -> dict:
    """Automated incident analysis using LLM."""
    analysis = await incident_intelligence.analyze_incident(
        incident_id=incident_id,
        incident_data=incident_data,
    )
    return {"success": True, "data": analysis.model_dump()}


@router.get("/incident-intelligence/correlations")
async def correlate_anomalies(
    time_window_hours: int = Query(2, ge=1, le=48, description="Time window in hours"),
) -> dict:
    """Correlate anomalies across the system."""
    correlations = await incident_intelligence.correlate_anomalies(
        time_window_hours=time_window_hours,
    )
    return {"success": True, "data": [c.model_dump() for c in correlations]}


@router.post("/incident-intelligence/root-cause")
async def suggest_root_cause(
    incident_id: str = Body(..., description="Incident ID"),
    incident_data: dict = Body(..., description="Incident data"),
    system_state: dict = Body({}, description="Current system state context"),
) -> dict:
    """Suggest likely root causes for an incident."""
    suggestion = await incident_intelligence.suggest_root_cause(
        incident_id=incident_id,
        incident_data=incident_data,
        system_state=system_state,
    )
    return {"success": True, "data": suggestion.model_dump()}
