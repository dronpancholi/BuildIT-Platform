"""
SEO Platform — Workflow Timeline Engine
==========================================
Logs granular campaign step progress into PostgreSQL and broadcasts
real-time updates via SSE so the frontend can show live progress.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from seo_platform.models.observability import CampaignTimelineEvent

logger = logging.getLogger(__name__)


class WorkflowTimelineService:
    """Persistent + real-time campaign step progression tracker."""

    async def record_step(
        self,
        tenant_id: UUID,
        campaign_id: UUID,
        step_name: str,
        status: str,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a timeline event and broadcast via SSE."""
        from seo_platform.core.database import get_db_session

        async with get_db_session() as session:
            event = CampaignTimelineEvent(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                step_name=step_name,
                status=status,
                message=message,
                step_metadata=metadata or {},
            )
            session.add(event)
            # flush to get the event id before broadcasting
            await session.flush()

        try:
            from seo_platform.api.endpoints.realtime.sse import emit_telemetry_event

            await emit_telemetry_event(
                tenant_id,
                "campaign_timeline",
                {
                    "campaign_id": str(campaign_id),
                    "step_name": step_name,
                    "status": status,
                    "message": message,
                    "metadata": metadata or {},
                },
            )
        except Exception:
            logger.exception("timeline_sse_broadcast_failed")

    async def get_campaign_timeline(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> list[dict[str, Any]]:
        """Return all timeline events for a campaign, ordered chronologically."""
        from sqlalchemy import select

        from seo_platform.core.database import get_db_session

        async with get_db_session() as session:
            result = await session.execute(
                select(CampaignTimelineEvent)
                .where(
                    CampaignTimelineEvent.tenant_id == tenant_id,
                    CampaignTimelineEvent.campaign_id == campaign_id,
                )
                .order_by(CampaignTimelineEvent.timestamp.asc())
            )
            rows = result.scalars().all()

        return [
            {
                "id": str(r.id),
                "step_name": r.step_name,
                "status": r.status,
                "message": r.message,
                "metadata": r.step_metadata,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in rows
        ]


workflow_timeline = WorkflowTimelineService()
