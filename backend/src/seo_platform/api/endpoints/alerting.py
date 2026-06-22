"""
Alerting API Endpoints — Phase 12G.2
=====================================
Endpoints for querying active alerts, acknowledging, and resolving.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from seo_platform.core.alerting import Severity, alert_manager
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    title: str
    message: str
    source: str
    status: str
    tenant_id: str
    created_at: float
    resolved_at: float | None = None
    escalation_count: int = 0


@router.get("")
async def list_alerts(severity: str | None = None):
    """List active alerts, optionally filtered by severity."""
    sev = Severity(severity) if severity else None
    alerts = alert_manager.get_active_alerts(severity=sev)
    return {
        "success": True,
        "data": {
            "total": len(alerts),
            "alerts": [
                AlertResponse(
                    id=a.id,
                    alert_type=a.alert_type,
                    severity=a.severity.value,
                    title=a.title,
                    message=a.message,
                    source=a.source,
                    status=a.status.value,
                    tenant_id=a.tenant_id,
                    created_at=a.created_at,
                    resolved_at=a.resolved_at,
                    escalation_count=a.escalation_count,
                )
                for a in alerts
            ],
        },
    }


@router.get("/summary")
async def alert_summary():
    """Get summary of active alerts by severity and status."""
    summary = alert_manager.get_alert_summary()
    return {"success": True, "data": summary}


class AckRequest(BaseModel):
    alert_id: str


@router.post("/acknowledge")
async def acknowledge_alert(req: AckRequest):
    """Acknowledge an active alert."""
    ok = alert_manager.acknowledge_alert(req.alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "message": "Alert acknowledged"}


class ResolveRequest(BaseModel):
    alert_id: str
    resolution_notes: str = ""


@router.post("/resolve")
async def resolve_alert(req: ResolveRequest):
    """Resolve an active alert."""
    ok = alert_manager.resolve_alert(req.alert_id, req.resolution_notes)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "message": "Alert resolved"}
