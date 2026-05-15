from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.governance_service import governance_service

router = APIRouter()


@router.get("/governance/audit-export")
async def export_audit_log(
    time_window_hours: int = Query(24, ge=1, le=720),
    export_format: str = Query("json", pattern="^(json|csv)$"),
) -> dict:
    export = await governance_service.export_audit_log(time_window_hours, export_format)
    return {"success": True, "data": export.model_dump()}


@router.get("/governance/compliance-report")
async def generate_compliance_report(
    standards: str | None = Query(None, description="Comma-separated standards"),
) -> dict:
    standards_list = standards.split(",") if standards else None
    report = await governance_service.generate_compliance_report(standards_list)
    return {"success": True, "data": report.model_dump()}


@router.get("/governance/lineage")
async def get_governance_lineage(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
) -> dict:
    lineage = await governance_service.get_governance_lineage(entity_type, entity_id)
    return {"success": True, "data": lineage.model_dump()}


@router.get("/governance/trace")
async def trace_operational_decision(
    decision_id: str = Query(...),
    workflow_id: str = Query(...),
) -> dict:
    trace = await governance_service.trace_operational_decision(decision_id, workflow_id)
    return {"success": True, "data": trace.model_dump()}


@router.get("/governance/rbac-hardening")
async def harden_rbac() -> dict:
    report = await governance_service.harden_rbac()
    return {"success": True, "data": report.model_dump()}


@router.get("/governance/infra-access-control")
async def assess_infra_access_controls() -> dict:
    control = await governance_service.assess_infra_access_controls()
    return {"success": True, "data": control.model_dump()}


@router.get("/governance/workflow-authorization")
async def assess_workflow_authorization_boundaries() -> dict:
    boundary = await governance_service.assess_workflow_authorization_boundaries()
    return {"success": True, "data": boundary.model_dump()}
