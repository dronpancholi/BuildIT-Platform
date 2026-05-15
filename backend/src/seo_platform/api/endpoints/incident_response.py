"""
SEO Platform — Incident Response Endpoints
============================================
REST endpoints for operational incident management.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Query

from seo_platform.services.incident_response import incident_response

router = APIRouter()


@router.post("/incident/incidents")
async def create_incident(
    title: str = Body(..., description="Incident title"),
    severity: str = Body(..., description="critical/high/medium/low"),
    category: str = Body(..., description="Incident category"),
    description: str = Body("", description="Detailed description"),
    affected_components: list[str] = Body([], description="Affected components"),
    detected_by: str = Body("system", description="Who detected the incident"),
) -> dict:
    """Create a tracked operational incident."""
    incident = await incident_response.create_incident(
        title=title,
        severity=severity,
        category=category,
        description=description,
        affected_components=affected_components,
        detected_by=detected_by,
    )
    return {"success": True, "data": incident.model_dump()}


@router.post("/incident/incidents/{incident_id}/timeline")
async def add_timeline_entry(
    incident_id: str,
    action: str = Body(..., description="Action performed"),
    actor: str = Body(..., description="Who performed the action"),
    detail: str = Body("", description="Detailed description"),
) -> dict:
    """Add a timeline entry to an incident."""
    entry = await incident_response.add_timeline_entry(
        incident_id=incident_id,
        action=action,
        actor=actor,
        detail=detail,
    )
    return {"success": True, "data": entry.model_dump()}


@router.post("/incident/incidents/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    summary: str = Body(..., description="Resolution summary"),
    resolution_notes: str = Body("", description="Detailed resolution notes"),
) -> dict:
    """Resolve an incident with summary and notes."""
    incident = await incident_response.resolve_incident(
        incident_id=incident_id,
        summary=summary,
        resolution_notes=resolution_notes,
    )
    return {"success": True, "data": incident.model_dump()}


@router.get("/incident/incidents")
async def list_active_incidents() -> dict:
    """List all active incidents."""
    incident_list = await incident_response.get_active_incidents()
    return {"success": True, "data": incident_list.model_dump()}


@router.get("/incident/incidents/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str) -> dict:
    """Get full timeline for an incident."""
    timeline = await incident_response.get_incident_timeline(
        incident_id=incident_id,
    )
    return {"success": True, "data": timeline.model_dump()}


@router.get("/incident/rollback-checklist")
async def get_rollback_checklist(
    deployment_id: str = Query(..., description="Deployment ID (service:version)"),
) -> dict:
    """Generate rollback readiness checklist for a deployment."""
    checklist = await incident_response.generate_rollback_checklist(
        deployment_id=deployment_id,
    )
    return {"success": True, "data": checklist.model_dump()}


@router.get("/incident/queue-intervention")
async def plan_queue_intervention(
    queue_name: str = Query(..., description="Queue name to intervene on"),
) -> dict:
    """Plan intervention for a problematic queue."""
    intervention = await incident_response.plan_queue_intervention(
        queue_name=queue_name,
    )
    return {"success": True, "data": intervention.model_dump()}


@router.get("/incident/workflow-recovery")
async def plan_workflow_recovery(
    workflow_id: str = Query(..., description="Workflow ID to recover"),
) -> dict:
    """Plan recovery for a failed or stuck workflow."""
    plan = await incident_response.plan_workflow_recovery(
        workflow_id=workflow_id,
    )
    return {"success": True, "data": plan.model_dump()}


@router.post("/incident/worker-action")
async def orchestrate_worker_action(
    worker_id: str = Body(..., description="Worker ID"),
    action: str = Body(..., description="drain/throttle/restart/scale_up"),
) -> dict:
    """Plan a worker orchestration action."""
    action_plan = await incident_response.orchestrate_worker_action(
        worker_id=worker_id,
        action=action,
    )
    return {"success": True, "data": action_plan.model_dump()}


@router.get("/incident/replay-debug")
async def analyze_replay_debug(
    workflow_id: str = Query(..., description="Workflow ID to debug"),
) -> dict:
    """Debug replay inconsistencies for a workflow."""
    session = await incident_response.analyze_replay_debug(
        workflow_id=workflow_id,
    )
    return {"success": True, "data": session.model_dump()}


@router.get("/incident/diagnostics")
async def generate_diagnostics() -> dict:
    """Comprehensive system diagnostics report."""
    report = await incident_response.generate_diagnostics()
    return {"success": True, "data": report.model_dump()}
