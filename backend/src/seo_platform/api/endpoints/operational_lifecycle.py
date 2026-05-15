from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.operational_lifecycle import operational_lifecycle

router = APIRouter()


@router.get("/operational-lifecycle/lifecycle-score")
async def get_lifecycle_score(
    service_id: str = Query(..., description="Service ID to score"),
):
    score = await operational_lifecycle.get_lifecycle_score(service_id)
    return {"success": True, "data": score.model_dump()}


@router.get("/operational-lifecycle/infrastructure-aging")
async def get_infrastructure_aging(
    service_id: str = Query(..., description="Service ID to analyze"),
):
    report = await operational_lifecycle.analyze_infrastructure_aging(service_id)
    return {"success": True, "data": report.model_dump()}


@router.get("/operational-lifecycle/dependency-lifecycle")
async def get_dependency_lifecycle(
    dep_id: str = Query(..., description="Dependency ID to track"),
):
    dep = await operational_lifecycle.track_dependency_lifecycle(dep_id)
    return {"success": True, "data": dep.model_dump()}


@router.get("/operational-lifecycle/degradation-forecast")
async def get_degradation_forecast(
    service_id: str = Query(..., description="Service ID to forecast"),
    horizon_days: int = Query(90, ge=7, le=365, description="Forecast horizon in days"),
):
    forecast = await operational_lifecycle.forecast_service_degradation(service_id, horizon_days)
    return {"success": True, "data": forecast.model_dump()}


@router.get("/operational-lifecycle/operational-entropy")
async def get_operational_entropy(
    service_id: str = Query(..., description="Service ID to analyze"),
):
    report = await operational_lifecycle.detect_operational_entropy(service_id)
    return {"success": True, "data": report.model_dump()}


@router.get("/operational-lifecycle/workflow-drift")
async def get_workflow_drift(
    workflow_type: str = Query(..., description="Workflow type to analyze"),
):
    report = await operational_lifecycle.detect_workflow_drift(workflow_type)
    return {"success": True, "data": report.model_dump()}


@router.get("/operational-lifecycle/infra-rot-prevention")
async def get_infra_rot_prevention(
    service_id: str = Query(..., description="Service ID to analyze"),
):
    plan = await operational_lifecycle.prevent_infra_rot(service_id)
    return {"success": True, "data": plan.model_dump()}


@router.get("/operational-lifecycle/sustainability-analytics")
async def get_sustainability_analytics(
    scope: str = Query("platform", description="Analytics scope"),
):
    analytics = await operational_lifecycle.get_sustainability_analytics(scope)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/operational-lifecycle/long-term-health-forecast")
async def get_long_term_health_forecast(
    service_id: str = Query(..., description="Service ID to forecast"),
    months: int = Query(12, ge=3, le=60, description="Forecast horizon in months"),
):
    forecast = await operational_lifecycle.forecast_long_term_health(service_id, months)
    return {"success": True, "data": forecast.model_dump()}
