"""
SEO Platform — Enterprise Lifecycle Infrastructure Endpoints
==============================================================
REST endpoints for enterprise onboarding, lifecycle, migration, compliance, governance.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Query

from seo_platform.services.enterprise_lifecycle import enterprise_lifecycle

router = APIRouter()


@router.post("/enterprise-lifecycle/onboarding")
async def onboard_enterprise(
    org_id: str = Body(..., description="Organization ID"),
) -> dict:
    """Initialize or retrieve enterprise onboarding status."""
    onboarding = await enterprise_lifecycle.onboard_enterprise(org_id)
    return {"success": True, "data": onboarding.model_dump()}


@router.get("/enterprise-lifecycle/organization-lifecycle")
async def get_organization_lifecycle(
    org_id: str = Query(..., description="Organization ID"),
) -> dict:
    """Assess organization lifecycle stage and churn risk."""
    lifecycle = await enterprise_lifecycle.assess_organization_lifecycle(org_id)
    return {"success": True, "data": lifecycle.model_dump()}


@router.post("/enterprise-lifecycle/migration-plan")
async def plan_migration(
    source_system: str = Body(..., description="Source system name"),
    target_system: str = Body(..., description="Target system name"),
) -> dict:
    """Plan an operational migration between systems."""
    migration = await enterprise_lifecycle.plan_operational_migration(source_system, target_system)
    return {"success": True, "data": migration.model_dump()}


@router.get("/enterprise-lifecycle/audit-export")
async def export_audit(
    time_range: str = Query("last_30_days", description="Time range for audit (last_24_hours, last_7_days, last_30_days, last_90_days)"),
    export_format: str = Query("json", description="Export format (json, csv)"),
) -> dict:
    """Export enterprise audit trail for the specified time range."""
    audit = await enterprise_lifecycle.export_enterprise_audit(time_range, export_format)
    return {"success": True, "data": audit.model_dump()}


@router.post("/enterprise-lifecycle/compliance-orchestration")
async def orchestrate_compliance(
    standards: list[str] = Body(None, description="Compliance standards to assess"),
) -> dict:
    """Orchestrate compliance assessment across specified standards."""
    compliance = await enterprise_lifecycle.orchestrate_compliance(standards)
    return {"success": True, "data": compliance.model_dump()}


@router.get("/enterprise-lifecycle/governance-assessment")
async def get_governance_assessment(
    governance_domain: str = Query(..., description="Governance domain (data_governance, access_control, security, operations, compliance)"),
) -> dict:
    """Assess operational governance for the specified domain."""
    governance = await enterprise_lifecycle.assess_operational_governance(governance_domain)
    return {"success": True, "data": governance.model_dump()}
