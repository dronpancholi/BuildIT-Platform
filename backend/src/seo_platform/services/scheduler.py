"""
SEO Platform — Phase 14 Service: Scheduler
===================================================
Implements a simple priority‑queue based scheduler persisting tasks to
`AgentTask`. Supports creation, cancellation, rescheduling, and
retrieval of the next ready task. Emits metrics for queue depth and
scheduling latency.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func, and_, desc

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import orchestrator_queue_depth, scheduler_latency_seconds
from seo_platform.models.agent import AgentTask, TaskStatus

logger = get_logger(__name__)

class SchedulerService:
    """Scheduler for AgentTask objects.

    All operations are tenant‑isolated. The scheduler updates Prometheus
    gauges to reflect queue depth and measures latency for task selection.
    """

    async def schedule_task(
        self,
        tenant_id: uuid.UUID,
        agent_instance_id: uuid.UUID,
        priority: int = 0,
        urgency: int = 0,
        plan_reference: Optional[uuid.UUID] = None,
        max_retries: int = 3,
        metadata: dict | None = None,
    ) -> AgentTask:
        """Create a new pending task for an agent instance."""
        async with get_tenant_session(tenant_id) as session:
            task = AgentTask(
                tenant_id=tenant_id,
                agent_instance_id=agent_instance_id,
                status=TaskStatus.PENDING,
                priority=priority,
                urgency=urgency,
                plan_reference=plan_reference,
                max_retries=max_retries,
                scheduled_at=datetime.utcnow(),
                metadata_json=metadata or {},
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)
            # Update queue depth metric
            await self._update_queue_depth(tenant_id, session)
            logger.info("task_scheduled", tenant_id=str(tenant_id), task_id=str(task.id), priority=priority, urgency=urgency)
            return task

    async def cancel_task(self, tenant_id: uuid.UUID, task_id: uuid.UUID) -> None:
        async with get_tenant_session(tenant_id) as session:
            await session.execute(
                update(AgentTask)
                .where(AgentTask.tenant_id == tenant_id, AgentTask.id == task_id)
                .values(status=TaskStatus.CANCELLED, completed_at=datetime.utcnow())
            )
            await session.flush()
            await self._update_queue_depth(tenant_id, session)
            logger.info("task_cancelled", tenant_id=str(tenant_id), task_id=str(task_id))

    async def reschedule_task(
        self,
        tenant_id: uuid.UUID,
        task_id: uuid.UUID,
        new_priority: Optional[int] = None,
        new_urgency: Optional[int] = None,
    ) -> AgentTask:
        async with get_tenant_session(tenant_id) as session:
            task = await session.get(AgentTask, task_id)
            if not task or task.tenant_id != tenant_id:
                raise ValueError("Task not found")
            if new_priority is not None:
                task.priority = new_priority
            if new_urgency is not None:
                task.urgency = new_urgency
            task.scheduled_at = datetime.utcnow()
            await session.flush()
            await session.refresh(task)
            await self._update_queue_depth(tenant_id, session)
            logger.info("task_rescheduled", tenant_id=str(tenant_id), task_id=str(task.id), priority=task.priority, urgency=task.urgency)
            return task

    async def next_task(self, tenant_id: uuid.UUID) -> Optional[AgentTask]:
        """Retrieve the highest‑priority pending task.

        Uses a weighted ordering: priority (desc), urgency (desc), created_at (asc).
        Returns None if no pending tasks.
        """
        start = datetime.utcnow()
        async with get_tenant_session(tenant_id) as session:
            stmt = (
                select(AgentTask)
                .where(AgentTask.tenant_id == tenant_id, AgentTask.status == TaskStatus.PENDING)
                .order_by(
                    desc(AgentTask.priority),
                    desc(AgentTask.urgency),
                    AgentTask.created_at,
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()
            # Update queue depth after selection (task still pending until marked running)
            await self._update_queue_depth(tenant_id, session)
            latency = (datetime.utcnow() - start).total_seconds()
            scheduler_latency_seconds.observe(latency, labels={"tenant_id": str(tenant_id)})
            if task:
                # Mark as scheduled (or running) – the orchestrator will transition later
                task.status = TaskStatus.SCHEDULED
                task.started_at = datetime.utcnow()
                await session.flush()
            return task

    async def _update_queue_depth(self, tenant_id: uuid.UUID, session) -> None:
        count = await session.execute(
            select(func.count()).select_from(AgentTask).where(
                AgentTask.tenant_id == tenant_id, AgentTask.status == TaskStatus.PENDING
            )
        )
        depth = count.scalar_one()
        orchestrator_queue_depth.labels(tenant_id=str(tenant_id)).set(depth)

# Export singleton
scheduler = SchedulerService()
