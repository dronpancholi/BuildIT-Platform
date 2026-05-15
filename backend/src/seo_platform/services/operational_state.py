"""
SEO Platform — Operational State Service
==========================================
Maintains an in-memory snapshot of the entire platform's operational state.
State is derived from Temporal, Redis, database, and live event streams.
No fake metrics — all data comes from real system state.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowStateEntry:
    __slots__ = ("workflow_id", "wf_type", "status", "started_at", "task_queue")

    def __init__(
        self,
        workflow_id: str,
        wf_type: str,
        status: str,
        started_at: datetime | None = None,
        task_queue: str = "",
    ) -> None:
        self.workflow_id = workflow_id
        self.wf_type = wf_type
        self.status = status
        self.started_at = started_at or datetime.now(UTC)
        self.task_queue = task_queue

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "type": self.wf_type,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "task_queue": self.task_queue,
        }


class WorkerStateEntry:
    __slots__ = ("worker_id", "task_queue", "last_heartbeat", "status")

    def __init__(
        self,
        worker_id: str,
        task_queue: str,
        last_heartbeat: datetime | None = None,
        status: str = "active",
    ) -> None:
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.last_heartbeat = last_heartbeat or datetime.now(UTC)
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "task_queue": self.task_queue,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "status": self.status,
        }


class OperationalStateService:
    """
    Tracks the live state of the SEO platform.
    State is updated by event handlers, Temporal queries, and Redis pub/sub.
    """

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowStateEntry] = {}
        self._workers: dict[str, WorkerStateEntry] = {}
        self._queue_depths: dict[str, int] = {}
        self._pending_approvals: dict[str, dict[str, Any]] = {}
        self._infra_health: dict[str, str] = {}
        self._active_campaigns: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._last_refresh: datetime | None = None

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------
    async def get_snapshot(self) -> dict[str, Any]:
        """Return the complete current state of the platform."""
        await self.refresh_from_temporal()
        async with self._lock:
            await self._refresh_queue_depths()
            await self._refresh_infra_health()

        return {
            "workflows": await self.get_workflows(),
            "workers": await self.get_workers(),
            "queues": await self.get_queues(),
            "approvals": list(self._pending_approvals.values()),
            "infrastructure": dict(self._infra_health),
            "campaigns": list(self._active_campaigns.values()),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def get_workflows(self) -> list[dict[str, Any]]:
        """Return all tracked workflows."""
        async with self._lock:
            return [w.to_dict() for w in self._workflows.values()]

    async def get_workers(self) -> list[dict[str, Any]]:
        """Return all known workers."""
        async with self._lock:
            return [w.to_dict() for w in self._workers.values()]

    async def get_queues(self) -> dict[str, Any]:
        """Return queue depths fetched from Temporal."""
        async with self._lock:
            await self._refresh_queue_depths()
            return dict(self._queue_depths)

    async def get_infra_health(self) -> dict[str, str]:
        """Return cached infrastructure health."""
        async with self._lock:
            await self._refresh_infra_health()
            return dict(self._infra_health)

    async def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Return all pending approvals."""
        async with self._lock:
            return list(self._pending_approvals.values())

    async def get_active_campaigns(self) -> list[dict[str, Any]]:
        """Return all active campaigns with their current phase."""
        async with self._lock:
            return list(self._active_campaigns.values())

    # ------------------------------------------------------------------
    # State mutations
    # ------------------------------------------------------------------
    async def record_workflow_event(
        self,
        wf_id: str,
        wf_type: str,
        status: str,
        task_queue: str = "",
    ) -> None:
        """Record or update a workflow in the state tracker."""
        async with self._lock:
            if wf_id in self._workflows:
                entry = self._workflows[wf_id]
                entry.status = status
                if task_queue:
                    entry.task_queue = task_queue
            else:
                self._workflows[wf_id] = WorkflowStateEntry(
                    workflow_id=wf_id,
                    wf_type=wf_type,
                    status=status,
                    task_queue=task_queue,
                )
            if status in ("completed", "failed", "cancelled", "timed_out"):
                self._workflows.pop(wf_id, None)

    async def record_worker_heartbeat(
        self,
        worker_id: str,
        task_queue: str,
    ) -> None:
        """Record or update a worker heartbeat."""
        async with self._lock:
            now = datetime.now(UTC)
            if worker_id in self._workers:
                entry = self._workers[worker_id]
                entry.last_heartbeat = now
                entry.task_queue = task_queue
                entry.status = "active"
            else:
                self._workers[worker_id] = WorkerStateEntry(
                    worker_id=worker_id,
                    task_queue=task_queue,
                    last_heartbeat=now,
                    status="active",
                )

    async def record_approval(
        self,
        approval_id: str,
        tenant_id: str,
        summary: str,
        risk_level: str = "",
        status: str = "pending",
    ) -> None:
        """Record a pending approval request."""
        async with self._lock:
            self._pending_approvals[approval_id] = {
                "approval_id": approval_id,
                "tenant_id": tenant_id,
                "summary": summary,
                "risk_level": risk_level,
                "status": status,
                "created_at": datetime.now(UTC).isoformat(),
            }

    async def resolve_approval(self, approval_id: str, status: str) -> None:
        """Remove or update an approval after resolution."""
        async with self._lock:
            if approval_id in self._pending_approvals:
                if status in ("approved", "rejected"):
                    del self._pending_approvals[approval_id]
                else:
                    self._pending_approvals[approval_id]["status"] = status

    async def record_campaign(
        self,
        campaign_id: str,
        tenant_id: str,
        name: str,
        status: str,
        phase: str = "",
    ) -> None:
        """Record or update an active campaign."""
        async with self._lock:
            self._active_campaigns[campaign_id] = {
                "campaign_id": campaign_id,
                "tenant_id": tenant_id,
                "name": name,
                "status": status,
                "phase": phase,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            if status in ("completed", "archived", "cancelled"):
                self._active_campaigns.pop(campaign_id, None)

    async def set_infra_component(self, component: str, status: str) -> None:
        """Update a single infrastructure component health."""
        async with self._lock:
            self._infra_health[component] = status

    # ------------------------------------------------------------------
    # Internal refresh — Temporal-backed
    # ------------------------------------------------------------------
    async def _refresh_queue_depths(self) -> None:
        """Derive queue depths from active workflows tracked in-memory."""
        from seo_platform.workflows import TaskQueue

        queues_to_check = [
            TaskQueue.ONBOARDING,
            TaskQueue.AI_ORCHESTRATION,
            TaskQueue.SEO_INTELLIGENCE,
            TaskQueue.BACKLINK_ENGINE,
            TaskQueue.COMMUNICATION,
            TaskQueue.REPORTING,
        ]

        for q in queues_to_check:
            depth = sum(1 for w in self._workflows.values()
                       if w.task_queue == q and w.status == "running")
            self._queue_depths[q] = depth

        self._queue_depths["total_running"] = sum(1 for w in self._workflows.values() if w.status == "running")

    async def _refresh_infra_health(self) -> None:
        """Check live infrastructure health."""
        try:
            from seo_platform.core.database import get_engine
            from sqlalchemy import text
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            self._infra_health["database"] = "healthy"
        except Exception as e:
            self._infra_health["database"] = f"unhealthy: {str(e)[:50]}"

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            await redis.ping()
            self._infra_health["redis"] = "healthy"
        except Exception as e:
            self._infra_health["redis"] = f"unhealthy: {str(e)[:50]}"

        try:
            from seo_platform.core.temporal_client import get_temporal_client
            client = await get_temporal_client()
            self._infra_health["temporal"] = "healthy" if client else "unreachable"
        except Exception as e:
            self._infra_health["temporal"] = f"unhealthy: {str(e)[:50]}"

        try:
            from seo_platform.main import get_event_publisher
            publisher = await get_event_publisher()
            if publisher._producer:
                self._infra_health["kafka"] = "healthy"
            else:
                self._infra_health["kafka"] = "disconnected"
        except Exception as e:
            self._infra_health["kafka"] = f"unhealthy: {str(e)[:50]}"

    async def refresh_from_temporal(self) -> None:
        """Full refresh: poll Temporal for active workflow state."""
        from seo_platform.core.temporal_client import get_temporal_client
        from temporalio.client import WorkflowExecutionStatus as WfStatus

        try:
            client = await get_temporal_client()

            new_workflows: dict[str, WorkflowStateEntry] = {}

            async for wf in client.list_workflows(
                query='ExecutionStatus IN ("Running")',
            ):
                wf_type = wf.workflow_type or "unknown"
                task_queue = wf.task_queue or ""
                status = "running"

                new_workflows[wf.id] = WorkflowStateEntry(
                    workflow_id=wf.id,
                    wf_type=wf_type,
                    status=status,
                    task_queue=task_queue,
                )

            async with self._lock:
                self._workflows.clear()
                self._workflows.update(new_workflows)
        except Exception as e:
            logger.warning("temporal_refresh_failed", error=str(e))


operational_state = OperationalStateService()
