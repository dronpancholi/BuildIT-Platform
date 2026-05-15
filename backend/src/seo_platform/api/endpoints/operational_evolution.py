from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.operational_evolution import operational_evolution

router = APIRouter()


@router.post("/operational-evolution/learn-pattern")
async def learn_operational_pattern(
    workflow_id: str = Query(..., description="Workflow ID to learn from"),
):
    pattern = await operational_evolution.learn_operational_pattern(workflow_id)
    return {"success": True, "data": pattern.model_dump()}


@router.get("/operational-evolution/workflow-optimization-memory")
async def get_workflow_optimization_memory(
    workflow_type: str = Query(..., description="Workflow type to recall"),
):
    memory = await operational_evolution.get_workflow_optimization_memory(workflow_type)
    return {"success": True, "data": memory.model_dump()}


@router.post("/operational-evolution/record-tuning")
async def record_infra_tuning(
    service_id: str = Query(..., description="Service ID tuned"),
    action: str = Query(..., description="Tuning action performed"),
):
    record = await operational_evolution.record_infra_tuning(service_id, action)
    return {"success": True, "data": record.model_dump()}


@router.get("/operational-evolution/historical-anomaly-learning")
async def get_historical_anomaly_learning(
    anomaly_type: str = Query(..., description="Anomaly type to learn from"),
):
    learning = await operational_evolution.learn_from_historical_anomalies(anomaly_type)
    return {"success": True, "data": learning.model_dump()}


@router.get("/operational-evolution/recommendation-evolution")
async def get_recommendation_evolution(
    recommendation_id: str = Query(..., description="Recommendation ID to track"),
):
    evolution = await operational_evolution.track_recommendation_evolution(recommendation_id)
    return {"success": True, "data": evolution.model_dump()}


@router.get("/operational-evolution/improvement-recommendations")
async def get_improvement_recommendations(
    scope: str = Query("platform", description="Scope for recommendations"),
):
    recs = await operational_evolution.generate_improvement_recommendations(scope)
    return {"success": True, "data": [r.model_dump() for r in recs]}


@router.get("/operational-evolution/recommendation-confidence")
async def get_recommendation_confidence(
    recommendation_id: str = Query(..., description="Recommendation ID"),
):
    confidence = await operational_evolution.get_recommendation_confidence(recommendation_id)
    return {"success": True, "data": confidence.model_dump()}


@router.get("/operational-evolution/recommendation-explanation")
async def get_recommendation_explanation(
    recommendation_id: str = Query(..., description="Recommendation ID"),
):
    explanation = await operational_evolution.explain_recommendation(recommendation_id)
    return {"success": True, "data": explanation.model_dump()}
