"""
SEO Platform — Advanced SRE & Operations Endpoints
=====================================================
REST endpoints for infra incident prediction, autonomous diagnostics,
workflow degradation forecasting, pressure prediction, anomaly intelligence,
and infra self-analysis.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.advanced_sre import advanced_sre

router = APIRouter()


@router.get("/advanced-sre/incident-predictions")
async def get_incident_predictions(
    lookahead_hours: int = Query(24, ge=1, le=168, description="Hours to look ahead for predictions"),
) -> dict:
    """Predict likely infrastructure incidents based on current system state."""
    predictions = await advanced_sre.predict_infra_incidents(lookahead_hours)
    return {"success": True, "data": [p.model_dump() for p in predictions]}


@router.get("/advanced-sre/autonomous-diagnostics")
async def get_autonomous_diagnostics(
    scope: str = Query("full", description="Diagnostic scope (full, quick)"),
) -> dict:
    """Run autonomous operational diagnostics and return findings."""
    diagnostics = await advanced_sre.run_autonomous_diagnostics(scope)
    return {"success": True, "data": diagnostics.model_dump()}


@router.get("/advanced-sre/workflow-degradation-forecast")
async def get_workflow_degradation_forecast(
    workflow_type: str = Query(..., description="Workflow type to forecast degradation for"),
    lookahead_hours: int = Query(24, ge=1, le=168, description="Hours to forecast ahead"),
) -> dict:
    """Forecast workflow degradation for a specific workflow type."""
    forecast = await advanced_sre.forecast_workflow_degradation(workflow_type, lookahead_hours)
    return {"success": True, "data": forecast.model_dump()}


@router.get("/advanced-sre/operational-pressure-prediction")
async def get_operational_pressure_prediction() -> dict:
    """Predict operational pressure across system components."""
    predictions = await advanced_sre.predict_operational_pressure()
    return {"success": True, "data": [p.model_dump() for p in predictions]}


@router.get("/advanced-sre/distributed-anomaly-intelligence")
async def get_distributed_anomaly_intelligence() -> dict:
    """Analyze distributed anomaly intelligence across the system."""
    anomalies = await advanced_sre.analyze_distributed_anomaly_intelligence()
    return {"success": True, "data": [a.model_dump() for a in anomalies]}


@router.get("/advanced-sre/infra-self-analysis")
async def get_infra_self_analysis() -> dict:
    """Run comprehensive infrastructure self-analysis."""
    report = await advanced_sre.run_infra_self_analysis()
    return {"success": True, "data": report.model_dump()}
