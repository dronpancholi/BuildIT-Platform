"""
Temporal Operations Center — Visibility into workflow execution.
Shows connection status, running workflows, failures, and provides control actions.
"""

from __future__ import annotations

from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text

from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def _check_temporal_connection() -> dict:
    """Check if Temporal server is reachable."""
    try:
        from seo_platform.core.temporal_client import get_temporal_client
        client = await get_temporal_client()
        # If we get here, Temporal is connected
        return {
            "status": "connected",
            "target": "localhost:7233",
            "message": "Temporal server is reachable",
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "target": "localhost:7233",
            "message": f"Temporal server unavailable: {type(e).__name__}",
            "error": str(e)[:200],
        }


@router.get("/temporal/status")
async def temporal_status(user: CurrentUser = Depends(get_current_user)):
    """Get Temporal connection status, worker info, and workflow summary."""
    temporal = await _check_temporal_connection()

    async with get_session() as session:
        # Count workflows by status from our DB tracking
        workflow_counts = {}
        try:
            rows = await session.execute(
                text("""
                    SELECT status, COUNT(*) as cnt
                    FROM backlink_campaigns
                    WHERE tenant_id = :tid
                    GROUP BY status
                """),
                {"tid": str(user.tenant_id)},
            )
            for r in rows.fetchall():
                workflow_counts[r[0]] = r[1]
        except Exception:
            pass

        # Count approval requests
        approval_counts = {}
        try:
            rows = await session.execute(
                text("""
                    SELECT status, COUNT(*) as cnt
                    FROM approval_requests
                    WHERE tenant_id = :tid
                    GROUP BY status
                """),
                {"tid": str(user.tenant_id)},
            )
            for r in rows.fetchall():
                approval_counts[r[0]] = r[1]
        except Exception:
            pass

        # Recent campaign activity
        recent_campaigns = []
        try:
            rows = await session.execute(
                text("""
                    SELECT id, name, status, created_at, updated_at
                    FROM backlink_campaigns
                    WHERE tenant_id = :tid
                    ORDER BY updated_at DESC LIMIT 10
                """),
                {"tid": str(user.tenant_id)},
            )
            for r in rows.fetchall():
                recent_campaigns.append({
                    "id": str(r.id),
                    "name": r.name,
                    "status": r.status,
                    "created_at": str(r.created_at),
                    "updated_at": str(r.updated_at),
                })
        except Exception:
            pass

        # Failed items
        failed_count = 0
        try:
            rows = await session.execute(
                text("""
                    SELECT COUNT(*) FROM citation_submissions
                    WHERE tenant_id = :tid AND status IN ('failed', 'rejected')
                """),
                {"tid": str(user.tenant_id)},
            )
            failed_count = rows.scalar() or 0
        except Exception:
            pass

    return {
        "success": True,
        "data": {
            "temporal": temporal,
            "campaigns": workflow_counts,
            "approvals": approval_counts,
            "recent_campaigns": recent_campaigns,
            "failed_submissions": failed_count,
            "queues": {
                "ONBOARDING": {"status": "ready" if temporal["status"] == "connected" else "blocked", " workflows": 0},
                "BACKLINK_ENGINE": {"status": "ready" if temporal["status"] == "connected" else "blocked", "workflows": 0},
                "COMMUNICATION": {"status": "ready" if temporal["status"] == "connected" else "blocked", "workflows": 0},
                "REPORTING": {"status": "ready" if temporal["status"] == "connected" else "blocked", "workflows": 0},
            },
        },
        "error": None,
    }


@router.get("/temporal/workflows")
async def list_workflows(user: CurrentUser = Depends(get_current_user)):
    """List all tracked workflows with status and details."""
    async with get_session() as session:
        campaigns = await session.execute(
            text("""
                SELECT id, name, status, campaign_type, created_at, updated_at,
                       client_id
                FROM backlink_campaigns
                WHERE tenant_id = :tid
                ORDER BY updated_at DESC
            """),
            {"tid": str(user.tenant_id)},
        )
        workflows = []
        for r in campaigns.fetchall():
            status_action = "none"
            if r.status == "draft":
                status_action = "launch"
            elif r.status == "active":
                status_action = "pause"
            elif r.status == "paused":
                status_action = "resume"
            elif r.status == "failed":
                status_action = "retry"

            workflows.append({
                "id": str(r.id),
                "name": r.name,
                "status": r.status,
                "type": r.campaign_type,
                "client_id": str(r.client_id),
                "created_at": str(r.created_at),
                "updated_at": str(r.updated_at),
                "available_actions": [status_action] if status_action != "none" else [],
            })

    return {
        "success": True,
        "data": workflows,
        "error": None,
    }


@router.post("/temporal/workflows/{workflow_id}/retry")
async def retry_workflow(
    workflow_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Retry a failed workflow."""
    async with get_session() as session:
        await session.execute(
            text("""
                UPDATE backlink_campaigns
                SET status = 'draft', updated_at = NOW()
                WHERE id = :id AND tenant_id = :tid AND status = 'failed'
            """),
            {"id": str(workflow_id), "tid": str(user.tenant_id)},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"message": "Workflow reset to draft. Click Launch to retry."},
        "error": None,
    }


@router.post("/temporal/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Cancel a running workflow."""
    async with get_session() as session:
        await session.execute(
            text("""
                UPDATE backlink_campaigns
                SET status = 'cancelled', updated_at = NOW()
                WHERE id = :id AND tenant_id = :tid AND status IN ('active', 'paused', 'draft')
            """),
            {"id": str(workflow_id), "tid": str(user.tenant_id)},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"message": "Workflow cancelled."},
        "error": None,
    }


@router.post("/temporal/workflows/{workflow_id}/pause")
async def pause_workflow(
    workflow_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Pause a running workflow."""
    async with get_session() as session:
        await session.execute(
            text("""
                UPDATE backlink_campaigns
                SET status = 'paused', updated_at = NOW()
                WHERE id = :id AND tenant_id = :tid AND status = 'active'
            """),
            {"id": str(workflow_id), "tid": str(user.tenant_id)},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"message": "Workflow paused."},
        "error": None,
    }


@router.post("/temporal/workflows/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Resume a paused workflow."""
    async with get_session() as session:
        await session.execute(
            text("""
                UPDATE backlink_campaigns
                SET status = 'active', updated_at = NOW()
                WHERE id = :id AND tenant_id = :tid AND status = 'paused'
            """),
            {"id": str(workflow_id), "tid": str(user.tenant_id)},
        )
        await session.commit()

    return {
        "success": True,
        "data": {"message": "Workflow resumed."},
        "error": None,
    }
