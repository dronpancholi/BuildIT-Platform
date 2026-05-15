"""
SEO Platform — Operational Loop Service
==========================================
Manages the continuous operational heartbeat of the platform.
Creates real events, drives the live feed, and orchestrates autonomous workflows.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from seo_platform.core.logging import get_logger
from seo_platform.core.temporal_client import get_temporal_client
from seo_platform.workflows import TaskQueue

logger = get_logger(__name__)


class OperationalLoopService:
    """
    Manages continuous operational activity.

    On startup:
    1. Creates the operational_events table if it doesn't exist
    2. Starts the OperationalLoopEngine Temporal workflow
    3. Registers cron schedules for recurring discovery workflows
    """

    def __init__(self) -> None:
        self._started = False

    async def ensure_table(self) -> None:
        """Create operational_events table if it doesn't exist."""
        from seo_platform.core.database import get_session
        from sqlalchemy import text

        try:
            async with get_session() as session:
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS operational_events (
                        id UUID PRIMARY KEY,
                        event_type VARCHAR(100) NOT NULL,
                        summary TEXT NOT NULL DEFAULT '',
                        severity VARCHAR(20) NOT NULL DEFAULT 'info',
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_operational_events_created_at
                    ON operational_events (created_at DESC)
                """))
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_operational_events_type
                    ON operational_events (event_type)
                """))
                await session.commit()
                logger.info("operational_events_table_ensured")
        except Exception as e:
            logger.warning("operational_events_table_failed", error=str(e))

    async def start(self) -> None:
        """Start the operational loop and register schedules."""
        if self._started:
            return
        self._started = True

        # 1. Ensure table exists
        await self.ensure_table()

        # 2. Start the continuous operational loop
        try:
            temporal = await get_temporal_client()
            tenant_id = "00000000-0000-0000-0000-000000000001"

            # Check if already running
            existing = False
            async for wf in temporal.list_workflows():
                if (
                    wf.workflow_type == "OperationalLoopEngine"
                    and wf.status.name == "RUNNING"
                ):
                    existing = True
                    logger.info("operational_loop_already_running", workflow_id=wf.id)
                    break

            if not existing:
                await temporal.start_workflow(
                    "OperationalLoopEngine",
                    args=[tenant_id],
                    id=f"operational-loop-{tenant_id}",
                    task_queue=TaskQueue.AI_ORCHESTRATION,
                )
                logger.info("operational_loop_started")

            # 3. Register cron schedules
            await self._register_schedules(temporal, tenant_id)

            # 4. Start Continuous Intelligence Loop
            existing_intelligence = False
            async for wf in temporal.list_workflows():
                if (
                    wf.workflow_type == "ContinuousIntelligenceLoop"
                    and wf.status.name == "RUNNING"
                ):
                    existing_intelligence = True
                    logger.info("continuous_intelligence_loop_already_running", workflow_id=wf.id)
                    break

            if not existing_intelligence:
                await temporal.start_workflow(
                    "ContinuousIntelligenceLoop",
                    args=[tenant_id],
                    id=f"continuous-intelligence-{tenant_id}",
                    task_queue=TaskQueue.AI_ORCHESTRATION,
                )
                logger.info("continuous_intelligence_loop_started")

        except Exception as e:
            logger.warning("operational_loop_start_failed", error=str(e))

    async def _register_schedules(
        self, temporal: Any, tenant_id: str
    ) -> None:
        """Register Temporal cron schedules for recurring workflows."""
        schedules = [
            {
                "id": f"health-scan-{tenant_id}",
                "workflow": "OperationalHealthScan",
                "cron": "*/5 * * * *",
                "args": [tenant_id],
                "queue": TaskQueue.AI_ORCHESTRATION,
            },
            {
                "id": f"discovery-{tenant_id}",
                "workflow": "AutonomousDiscovery",
                "cron": "0 * * * *",
                "args": [tenant_id],
                "queue": TaskQueue.BACKLINK_ENGINE,
            },
        ]

        for s in schedules:
            try:
                existing = False
                async for wf in temporal.list_workflows():
                    if wf.id == s["id"] and wf.status.name in ("RUNNING", "COMPLETED"):
                        existing = True
                        break

                if not existing:
                    await temporal.start_workflow(
                        s["workflow"],
                        args=s["args"],
                        id=s["id"],
                        task_queue=s["queue"],
                        cron_schedule=s["cron"],
                    )
                    logger.info(
                        "schedule_registered",
                        schedule_id=s["id"],
                        cron=s["cron"],
                    )
            except Exception as e:
                logger.warning(
                    "schedule_registration_failed",
                    schedule_id=s["id"],
                    error=str(e),
                )


# Global singleton
operational_loop = OperationalLoopService()
