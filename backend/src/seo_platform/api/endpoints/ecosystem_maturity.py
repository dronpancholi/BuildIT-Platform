from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.ecosystem_maturity import ecosystem_maturity

router = APIRouter()


@router.get("/ecosystem-maturity/integration-lifecycle")
async def get_integration_lifecycle(
    integration_id: str = Query(..., description="Integration ID"),
):
    result = await ecosystem_maturity.analyze_integration_lifecycle(integration_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/ecosystem-maturity/ecosystem-intelligence")
async def get_ecosystem_intelligence(
    scope: str = Query("platform", description="Ecosystem scope"),
):
    report = await ecosystem_maturity.orchestrate_ecosystem_intelligence(scope)
    return {"success": True, "data": report.model_dump()}


@router.get("/ecosystem-maturity/organization-governance")
async def get_organization_governance(
    org_id: str = Query(..., description="Organization ID"),
):
    report = await ecosystem_maturity.govern_organization_level(org_id)
    return {"success": True, "data": report.model_dump()}


@router.get("/ecosystem-maturity/cross-system-trace")
async def get_cross_system_trace(
    workflow_id: str = Query(..., description="Workflow ID"),
):
    trace = await ecosystem_maturity.trace_cross_system(workflow_id)
    return {"success": True, "data": trace.model_dump()}


@router.get("/ecosystem-maturity/compliance-evolution")
async def get_compliance_evolution(
    org_id: str = Query(..., description="Organization ID"),
):
    report = await ecosystem_maturity.evolve_operational_compliance(org_id)
    return {"success": True, "data": report.model_dump()}
