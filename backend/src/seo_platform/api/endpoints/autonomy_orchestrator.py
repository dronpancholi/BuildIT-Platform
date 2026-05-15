from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.autonomy_orchestrator import autonomy_orchestrator

router = APIRouter()


@router.get("/autonomy/workflow-suggestions")
async def get_workflow_suggestions(tenant_id: UUID = Query(...)) -> dict:
    suggestions = await autonomy_orchestrator.get_autonomous_workflow_suggestions(tenant_id)
    return {
        "success": True,
        "data": [s.model_dump() for s in suggestions],
        "count": len(suggestions),
    }


@router.get("/autonomy/infra-recommendations")
async def get_infra_recommendations() -> dict:
    recommendations = await autonomy_orchestrator.get_adaptive_infra_recommendations()
    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
    }


@router.post("/autonomy/self-analysis")
async def run_self_analysis() -> dict:
    report = await autonomy_orchestrator.run_self_analysis()
    return {"success": True, "data": report.model_dump()}


@router.get("/autonomy/optimization-intelligence")
async def get_optimization_intelligence(tenant_id: UUID = Query(...)) -> dict:
    suggestions = await autonomy_orchestrator.get_optimization_intelligence(tenant_id)
    return {
        "success": True,
        "data": [s.model_dump() for s in suggestions],
        "count": len(suggestions),
    }


@router.get("/autonomy/strategic-guidance")
async def get_strategic_guidance(tenant_id: UUID = Query(...)) -> dict:
    guidance = await autonomy_orchestrator.get_strategic_guidance(tenant_id)
    return {"success": True, "data": guidance.model_dump()}
