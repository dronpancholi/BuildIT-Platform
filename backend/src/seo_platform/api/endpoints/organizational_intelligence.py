from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.organizational_intelligence import organizational_intelligence

router = APIRouter()


@router.get("/organizational-intelligence/workflow-intelligence")
async def get_org_workflow_intelligence(
    org_id: str = Query(..., description="Organization ID"),
):
    result = await organizational_intelligence.analyze_org_workflow_intelligence(org_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/organizational-intelligence/team-coordination")
async def get_team_coordination(
    team_id: str = Query(..., description="Team ID"),
):
    result = await organizational_intelligence.analyze_team_coordination(team_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/organizational-intelligence/approval-bottlenecks")
async def get_approval_bottlenecks(
    org_id: str = Query(..., description="Organization ID"),
):
    result = await organizational_intelligence.analyze_approval_bottlenecks(org_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/organizational-intelligence/operational-productivity")
async def get_operational_productivity(
    org_id: str = Query(..., description="Organization ID"),
):
    result = await organizational_intelligence.measure_operational_productivity(org_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/organizational-intelligence/efficiency-forecast")
async def get_efficiency_forecast(
    org_id: str = Query(..., description="Organization ID"),
    months: int = Query(12, ge=3, le=60),
):
    result = await organizational_intelligence.forecast_enterprise_efficiency(org_id, months)
    return {"success": True, "data": result.model_dump()}


@router.get("/organizational-intelligence/operational-hierarchy")
async def get_operational_hierarchy(
    org_id: str = Query(..., description="Organization ID"),
):
    result = await organizational_intelligence.map_operational_hierarchy(org_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/organizational-intelligence/dependency-map")
async def get_organizational_dependency_map(
    org_id: str = Query(..., description="Organization ID"),
):
    result = await organizational_intelligence.map_organizational_dependencies(org_id)
    return {"success": True, "data": result.model_dump()}
