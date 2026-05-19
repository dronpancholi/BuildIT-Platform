"""
SEO Platform — Campaign Timeline API
========================================
Exposes detailed step-by-step progress for backlink campaign workflows.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.workflow_timeline import workflow_timeline

router = APIRouter()


@router.get("/campaigns/{campaign_id}/timeline")
async def get_campaign_timeline(
    campaign_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant UUID"),
):
    """Return all timeline events for a campaign, ordered chronologically."""
    events = await workflow_timeline.get_campaign_timeline(tenant_id, campaign_id)
    return {"success": True, "data": {"campaign_id": str(campaign_id), "events": events}}
