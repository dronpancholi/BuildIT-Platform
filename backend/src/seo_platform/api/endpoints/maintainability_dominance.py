from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.maintainability_dominance import maintainability_dominance

router = APIRouter()


@router.get("/maintainability-dominance/migration-readiness")
async def get_migration_readiness(
    component: str = Query(..., description="Component to assess"),
):
    result = await maintainability_dominance.assess_migration_readiness(component)
    return {"success": True, "data": result.model_dump()}


@router.get("/maintainability-dominance/schema-evolution")
async def get_schema_evolution(
    entity: str = Query(..., description="Entity to analyze"),
):
    result = await maintainability_dominance.analyze_schema_evolution(entity)
    return {"success": True, "data": result.model_dump()}


@router.get("/maintainability-dominance/api-governance")
async def get_api_governance(
    api_spec: str = Query("current", description="API spec version to govern"),
):
    result = await maintainability_dominance.govern_api_evolution(api_spec)
    return {"success": True, "data": result.model_dump()}


@router.get("/maintainability-dominance/event-contract-governance")
async def get_event_contract_governance(
    contract_id: str = Query(..., description="Event contract ID to validate"),
):
    result = await maintainability_dominance.govern_event_contracts(contract_id)
    return {"success": True, "data": result.model_dump()}


@router.get("/maintainability-dominance/temporal-versioning")
async def get_temporal_versioning(
    workflow_type: str = Query(..., description="Workflow type to analyze"),
):
    result = await maintainability_dominance.automate_temporal_versioning(workflow_type)
    return {"success": True, "data": result.model_dump()}


@router.get("/maintainability-dominance/infra-compatibility")
async def get_infra_compatibility(
    component: str = Query(..., description="Component to check"),
    target: str = Query(..., description="Target environment"),
):
    result = await maintainability_dominance.analyze_infra_compatibility(component, target)
    return {"success": True, "data": result.model_dump()}


@router.get("/maintainability-dominance/upgrade-safety")
async def get_upgrade_safety(
    component: str = Query(..., description="Component to upgrade"),
    target_version: str = Query(..., description="Target version"),
):
    result = await maintainability_dominance.assess_upgrade_safety(component, target_version)
    return {"success": True, "data": result.model_dump()}


@router.post("/maintainability-dominance/compatibility-simulation")
async def post_compatibility_simulation(
    component: str = Query(..., description="Component to simulate"),
    changes: str = Query(..., description="JSON array of changes to simulate"),
):
    import json
    parsed_changes = json.loads(changes)
    result = await maintainability_dominance.simulate_compatibility(component, parsed_changes)
    return {"success": True, "data": result.model_dump()}


@router.get("/maintainability-dominance/maintainability-score")
async def get_maintainability_score(
    component: str = Query(..., description="Component to score"),
):
    result = await maintainability_dominance.get_maintainability_score(component)
    return {"success": True, "data": result.model_dump()}
