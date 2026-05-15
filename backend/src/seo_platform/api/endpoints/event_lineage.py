"""
SEO Platform — Event Lineage REST Endpoints
=============================================
REST API for querying event causality chains and correlation trees.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from seo_platform.services.event_lineage import event_lineage

router = APIRouter()


@router.get("/event-lineage/{event_id}")
async def get_event_lineage(event_id: str):
    """
    Return the full causality chain for an event.

    Traces causation_id links backwards from the given event
    to the root cause. Ordered from root to leaf.
    """
    chain = await event_lineage.get_event_lineage(event_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"success": True, "data": {"event_id": event_id, "lineage": chain}}


@router.get("/event-lineage/tree/{correlation_id}")
async def get_event_tree(correlation_id: str):
    """
    Return all events in a correlation tree.

    Events are organized in a nested structure showing
    parent-child relationships via causation_id links.
    """
    tree = await event_lineage.get_event_tree(correlation_id)
    return {"success": True, "data": tree}


@router.get("/event-lineage/timeline")
async def get_event_timeline(
    source_service: str = Query(..., description="Source service name"),
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours"),
):
    """
    Return recent events from a source service within the given time window.
    """
    events = await event_lineage.get_event_timeline(source_service, hours)
    return {
        "success": True,
        "data": {
            "source_service": source_service,
            "time_window_hours": hours,
            "events": events,
        },
    }
