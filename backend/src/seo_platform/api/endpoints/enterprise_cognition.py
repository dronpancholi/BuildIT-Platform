from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Query

from seo_platform.services.enterprise_cognition import enterprise_cognition

router = APIRouter()


@router.get("/enterprise-cognition/history")
async def get_operational_history(
    tenant_id: UUID = Query(...),
    days: int = Query(7, ge=1, le=365),
) -> dict:
    history = await enterprise_cognition.reconstruct_operational_history(tenant_id, days)
    return {"success": True, "data": history.model_dump()}


@router.get("/enterprise-cognition/campaign-memory")
async def get_campaign_memory(
    tenant_id: UUID = Query(...),
    campaign_id: UUID = Query(...),
) -> dict:
    graph = await enterprise_cognition.build_campaign_memory_graph(tenant_id, campaign_id)
    return {"success": True, "data": graph.model_dump()}


@router.post("/enterprise-cognition/workflow-reasoning")
async def get_workflow_reasoning(
    workflow_type: str = Body(...),
    time_window_hours: int = Body(168, ge=1),
) -> dict:
    reasoning = await enterprise_cognition.reason_about_workflow_history(
        workflow_type, time_window_hours,
    )
    return {"success": True, "data": reasoning.model_dump()}


@router.get("/enterprise-cognition/organization-intelligence")
async def get_organization_intelligence(
    tenant_id: UUID = Query(...),
    days: int = Query(30, ge=1, le=365),
) -> dict:
    report = await enterprise_cognition.analyze_organization_intelligence(tenant_id, days)
    return {"success": True, "data": report.model_dump()}


@router.get("/enterprise-cognition/summary")
async def get_operational_summary(
    tenant_id: UUID = Query(...),
    time_window_hours: int = Query(24, ge=1, le=720),
) -> dict:
    summary = await enterprise_cognition.generate_operational_summary(tenant_id, time_window_hours)
    return {"success": True, "data": summary.model_dump()}


@router.get("/enterprise-cognition/strategic-context")
async def get_strategic_context(
    tenant_id: UUID = Query(...),
) -> dict:
    context = await enterprise_cognition.build_strategic_context(tenant_id)
    return {"success": True, "data": context.model_dump()}
