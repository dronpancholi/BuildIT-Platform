from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Query

from seo_platform.services.enterprise_ecosystem import enterprise_ecosystem

router = APIRouter()


@router.get("/enterprise-ecosystem/organization-intelligence")
async def get_organization_intelligence(
    org_id: str = Query(...),
) -> dict:
    intelligence = await enterprise_ecosystem.get_organization_intelligence(org_id)
    return {"success": True, "data": intelligence.model_dump()}


@router.get("/enterprise-ecosystem/department-analysis")
async def get_department_analysis(
    department: str = Query(...),
) -> dict:
    analysis = await enterprise_ecosystem.analyze_department_operations(department)
    return {"success": True, "data": analysis.model_dump()}


@router.get("/enterprise-ecosystem/cross-team-coordination")
async def get_cross_team_coordination() -> dict:
    coordinations = await enterprise_ecosystem.get_cross_team_coordination()
    return {
        "success": True,
        "data": [c.model_dump() for c in coordinations],
        "count": len(coordinations),
    }


@router.get("/enterprise-ecosystem/operational-hierarchy")
async def get_operational_hierarchy() -> dict:
    hierarchy = await enterprise_ecosystem.build_operational_hierarchy()
    return {"success": True, "data": hierarchy.model_dump()}


@router.get("/enterprise-ecosystem/organizational-performance")
async def get_organizational_performance(
    org_id: str = Query(...),
) -> dict:
    performance = await enterprise_ecosystem.analyze_organizational_performance(org_id)
    return {"success": True, "data": performance.model_dump()}


@router.get("/enterprise-ecosystem/campaign-orchestration")
async def get_campaign_orchestration(
    campaign_id: str = Query(...),
) -> dict:
    orchestration = await enterprise_ecosystem.orchestrate_enterprise_campaign(campaign_id)
    return {"success": True, "data": orchestration.model_dump()}


@router.get("/enterprise-ecosystem/organizational-graph")
async def get_organizational_graph() -> dict:
    graph = await enterprise_ecosystem.build_organizational_graph()
    return {"success": True, "data": graph.model_dump()}


@router.get("/enterprise-ecosystem/operational-dependencies")
async def get_operational_dependencies() -> dict:
    mapping = await enterprise_ecosystem.map_operational_dependencies()
    return {"success": True, "data": mapping.model_dump()}


@router.post("/enterprise-ecosystem/strategic-coordination")
async def post_strategic_coordination(
    coordination_type: str = Body(...),
    participants: list[str] = Body(...),
    objective: str = Body(...),
) -> dict:
    plan = await enterprise_ecosystem.plan_strategic_coordination(
        coordination_type, participants, objective,
    )
    return {"success": True, "data": plan.model_dump()}
