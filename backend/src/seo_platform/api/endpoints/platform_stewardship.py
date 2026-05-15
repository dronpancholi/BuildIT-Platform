from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.platform_stewardship import platform_stewardship

router = APIRouter()


@router.get("/platform-stewardship/stewardship-assessment")
async def get_stewardship_assessment(
    scope: str = Query("platform", description="Assessment scope"),
):
    result = await platform_stewardship.assess_operational_stewardship(scope)
    return {"success": True, "data": result.model_dump()}


@router.get("/platform-stewardship/infra-governance-dashboard")
async def get_infra_governance_dashboard(
    scope: str = Query("platform", description="Dashboard scope"),
):
    dashboard = await platform_stewardship.get_infra_governance_dashboard(scope)
    return {"success": True, "data": dashboard.model_dump()}


@router.get("/platform-stewardship/lifecycle-governance")
async def get_lifecycle_governance(
    service_id: str = Query(..., description="Service ID"),
):
    result = await platform_stewardship.govern_lifecycle(service_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/platform-stewardship/operational-quality-score")
async def get_operational_quality_score(
    service_id: str = Query(..., description="Service ID"),
):
    score = await platform_stewardship.score_operational_quality(service_id)
    return {"success": True, "data": score.model_dump()}


@router.get("/platform-stewardship/maintainability-governance")
async def get_maintainability_governance(
    component_id: str = Query(..., description="Component ID"),
):
    result = await platform_stewardship.govern_maintainability(component_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/platform-stewardship/platform-sustainability")
async def get_platform_sustainability(
    scope: str = Query("platform", description="Sustainability scope"),
):
    report = await platform_stewardship.assess_platform_sustainability(scope)
    return {"success": True, "data": report.model_dump()}
