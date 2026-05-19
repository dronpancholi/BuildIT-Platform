"""
SEO Platform — Demo Scenarios API
====================================
Manages pre-built demo environment injection and readiness validation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from seo_platform.services.demo_validator import demo_validator
from seo_platform.services.scenario_manager import scenario_manager

router = APIRouter()


@router.get("/demo/readiness")
async def get_demo_readiness():
    """Pre-flight check of PostgreSQL, Redis, Temporal, and data health."""
    result = await demo_validator.validate_system_integrity()
    return {"success": True, "data": result}


@router.get("/demo/scenarios")
async def list_demo_scenarios():
    """Return all available demo scenarios."""
    scenarios = scenario_manager.list_scenarios()
    return {"success": True, "data": {"scenarios": scenarios}}


@router.post("/demo/scenarios/load")
async def load_demo_scenario(
    name: str = Query(..., description="Scenario name (TechStart, LocalFlorist)"),
    tenant_id: UUID = Query(..., description="Target tenant UUID"),
):
    """Inject a pre-built demo scenario into the specified tenant."""
    try:
        result = await scenario_manager.load_scenario(tenant_id, name)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
