from __future__ import annotations

from fastapi import APIRouter, Body, Query

from seo_platform.services.maintainability_service import maintainability_service

router = APIRouter()


@router.post("/maintainability/workflow-migration-plan")
async def plan_workflow_migration(
    source_version: str = Body(...),
    target_version: str = Body(...),
) -> dict:
    plan = await maintainability_service.plan_workflow_migration(source_version, target_version)
    return {"success": True, "data": plan.model_dump()}


@router.get("/maintainability/event-schema-evolution")
async def track_event_schema_evolution() -> dict:
    evolution = await maintainability_service.track_event_schema_evolution()
    return {"success": True, "data": evolution.model_dump()}


@router.get("/maintainability/temporal-versioning")
async def assess_temporal_versioning() -> dict:
    assessment = await maintainability_service.assess_temporal_versioning()
    return {"success": True, "data": assessment.model_dump()}


@router.get("/maintainability/replay-compatibility")
async def assess_replay_compatibility(
    workflow_type: str = Query(...),
    source_version: str = Query(...),
    target_version: str = Query(...),
) -> dict:
    result = await maintainability_service.assess_replay_compatibility(
        workflow_type, source_version, target_version,
    )
    return {"success": True, "data": result.model_dump()}


@router.get("/maintainability/long-term")
async def assess_long_term_maintainability(
    service_name: str = Query(..., description="Service name to assess"),
) -> dict:
    assessment = await maintainability_service.assess_long_term_maintainability(service_name)
    return {"success": True, "data": assessment.model_dump()}


@router.get("/maintainability/service-dependencies")
async def govern_service_dependencies() -> dict:
    governance = await maintainability_service.govern_service_dependencies()
    return {"success": True, "data": governance.model_dump()}


@router.get("/maintainability/platform-lifecycle")
async def assess_platform_lifecycle() -> dict:
    lifecycle = await maintainability_service.assess_platform_lifecycle()
    return {"success": True, "data": lifecycle.model_dump()}
