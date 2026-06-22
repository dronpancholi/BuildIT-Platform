"""
SEO Platform — Demo Scenarios API
===================================
Phase 3 operator-readiness: synthetic data injection is disabled. The
/demo/scenarios/load and /demo/reset endpoints are kept as no-ops that
return a clear operator-facing message. /demo/readiness and
/demo/scenarios (list) still work for inspection.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, HTTPException, Query

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
    """Return all available demo scenarios (read-only)."""
    scenarios = scenario_manager.list_scenarios()
    return {"success": True, "data": {"scenarios": scenarios}}


@router.post("/demo/scenarios/load")
async def load_demo_scenario(
    name: str = Query(..., description="Scenario name (TechStart, LocalFlorist)"),
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Disabled in operator mode. Use /api/v1/identity/onboard to create
    a real tenant and add real data via Clients → Campaigns."""
    raise HTTPException(
        status_code=410,
        detail=(
            "Demo scenario loading is disabled. "
            "Use the real onboarding flow: POST /api/v1/identity/onboard "
            "to create a tenant, then POST /api/v1/clients and "
            "POST /api/v1/campaigns to add real data."
        ),
    )


@router.post("/demo/reset")
async def reset_demo_workspace(
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Disabled. Contact your platform engineer to reset a tenant."""
    raise HTTPException(
        status_code=410,
        detail=(
            "Demo reset is disabled. To start fresh, use the onboarding flow "
            "or contact your platform engineer."
        ),
    )
