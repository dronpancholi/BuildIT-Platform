from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.autonomous_coordination import autonomous_coordination

router = APIRouter()


@router.get("/autonomous-coordination/orchestration-optimizations")
async def get_orchestration_optimizations() -> dict:
    optimizations = await autonomous_coordination.get_orchestration_optimizations()
    return {
        "success": True,
        "data": [o.model_dump() for o in optimizations],
        "count": len(optimizations),
    }


@router.get("/autonomous-coordination/allocation-recommendations")
async def get_allocation_recommendations() -> dict:
    recommendations = await autonomous_coordination.get_infra_allocation_recommendations()
    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
    }


@router.get("/autonomous-coordination/workflow-coordination")
async def get_workflow_coordination(
    workflow_type: str = Query(..., description="Workflow type to analyze"),
) -> dict:
    intelligence = await autonomous_coordination.get_workflow_coordination_intelligence(workflow_type)
    return {"success": True, "data": intelligence.model_dump()}


@router.get("/autonomous-coordination/strategic-recommendations")
async def get_strategic_recommendations() -> dict:
    recommendations = await autonomous_coordination.get_strategic_operational_recommendations()
    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
    }


@router.get("/autonomous-coordination/enterprise-optimizations")
async def get_enterprise_optimizations() -> dict:
    suggestions = await autonomous_coordination.get_enterprise_optimization_suggestions()
    return {
        "success": True,
        "data": [s.model_dump() for s in suggestions],
        "count": len(suggestions),
    }
