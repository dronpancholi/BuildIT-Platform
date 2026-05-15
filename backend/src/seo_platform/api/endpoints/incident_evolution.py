from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.incident_evolution import incident_evolution

router = APIRouter()


@router.get("/incident-evolution/historical-analysis")
async def get_historical_incident_analysis(
    service_id: str = Query(..., description="Service ID"),
):
    result = await incident_evolution.analyze_historical_incidents(service_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/incident-evolution/incident-patterns")
async def get_incident_patterns(
    incident_type: str = Query(..., description="Incident type to learn from"),
):
    patterns = await incident_evolution.learn_incident_patterns(incident_type)
    return {"success": True, "data": [p.model_dump() for p in patterns]}


@router.get("/incident-evolution/postmortem")
async def get_postmortem(
    incident_id: str = Query(..., description="Incident ID"),
):
    report = await incident_evolution.generate_postmortem(incident_id)
    return {"success": True, "data": report.model_dump()}


@router.get("/incident-evolution/failure-lineage")
async def get_failure_lineage(
    incident_id: str = Query(..., description="Incident ID"),
):
    lineage = await incident_evolution.analyze_failure_lineage(incident_id)
    return {"success": True, "data": lineage.model_dump()}


@router.get("/incident-evolution/incident-replay-cognition")
async def get_incident_replay_cognition(
    incident_id: str = Query(..., description="Incident ID"),
):
    cognition = await incident_evolution.replay_incident_cognition(incident_id)
    return {"success": True, "data": cognition.model_dump()}


@router.get("/incident-evolution/incident-recommendations")
async def get_incident_recommendations(
    service_id: str = Query(..., description="Service ID"),
):
    recs = await incident_evolution.generate_incident_recommendations(service_id)
    return {"success": True, "data": [r.model_dump() for r in recs]}


@router.get("/incident-evolution/operational-learning-memory")
async def get_operational_learning_memory(
    scope: str = Query("platform", description="Scope for learning memory"),
):
    memory = await incident_evolution.build_operational_learning_memory(scope)
    return {"success": True, "data": memory.model_dump()}
