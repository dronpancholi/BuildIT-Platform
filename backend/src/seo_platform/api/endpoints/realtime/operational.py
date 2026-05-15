"""
SEO Platform — Operational State REST Endpoints
=================================================
REST endpoints exposing the current operational state of the platform.
All state is derived from real system data (Temporal, Redis, database).
No fake metrics.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from seo_platform.core.logging import get_logger
from seo_platform.services.operational_state import operational_state

logger = get_logger(__name__)

router = APIRouter()


@router.get("/state/{tenant_id}")
async def get_operational_state(tenant_id: str):
    """
    Return the complete current operational state for a tenant.
    Includes: workflows, workers, queues, approvals, campaigns, infra health.
    """
    try:
        UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")

    snapshot = await operational_state.get_snapshot()
    return {"success": True, "data": snapshot}


@router.get("/workflows/{tenant_id}")
async def get_active_workflows(tenant_id: str):
    """
    Return all active workflows for a tenant.
    """
    try:
        UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")

    workflows = await operational_state.get_workflows()
    return {"success": True, "data": {"workflows": workflows}}


@router.get("/queues")
async def get_queue_state():
    """
    Return current queue depths from Temporal for all task queues.
    """
    queues = await operational_state.get_queues()
    return {"success": True, "data": {"queues": queues}}


@router.get("/workers")
async def get_worker_state():
    """
    Return all known workers and their heartbeat state.
    """
    workers = await operational_state.get_workers()
    return {"success": True, "data": {"workers": workers}}
