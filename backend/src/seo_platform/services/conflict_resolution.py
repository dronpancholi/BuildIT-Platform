"""Conflict Resolution Service – deterministic resolution of AgentConflicts.

Provides three simple strategies:
* ``highest_priority`` – keep the highest‑priority task, cancel the rest.
* ``cancel`` – cancel all tasks involved in the conflict.
* ``escalate`` – mark the conflict as ``ESCALATED`` for manual handling.

All operations are tenant‑isolated, audited, and emit a Prometheus metric.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import conflict_resolution_total
from seo_platform.models.agent import AgentConflict, AgentTask, ConflictStatus, TaskStatus
from seo_platform.models.audit_ledger import AuditLedgerEntry

logger = get_logger(__name__)


class ConflictResolutionService:
    """Stateless service that resolves an ``AgentConflict`` using a chosen strategy."""

    async def resolve(self, tenant_id: uuid.UUID, conflict_id: uuid.UUID, strategy: str) -> AgentConflict:
        async with get_tenant_session(tenant_id) as session:
            conflict = await session.get(AgentConflict, conflict_id)
            if not conflict or conflict.tenant_id != tenant_id:
                raise ValueError("Conflict not found")

            if strategy == "highest_priority":
                exec_id = conflict.metadata_json.get("execution_id") if isinstance(conflict.metadata_json, dict) else None
                if not exec_id:
                    raise ValueError("No execution_id in conflict metadata")
                tasks_stmt = select(AgentTask).where(
                    AgentTask.tenant_id == tenant_id,
                    AgentTask.execution_reference == uuid.UUID(exec_id),
                    AgentTask.status != TaskStatus.COMPLETED,
                )
                result = await session.execute(tasks_stmt)
                tasks = result.scalars().all()
                if not tasks:
                    raise ValueError("No tasks found for conflict")
                # Keep highest priority, cancel the rest
                tasks.sort(key=lambda t: t.priority, reverse=True)
                keeper = tasks[0]
                for t in tasks[1:]:
                    t.status = TaskStatus.CANCELLED
                    t.completed_at = datetime.utcnow()
            elif strategy == "cancel":
                exec_id = conflict.metadata_json.get("execution_id") if isinstance(conflict.metadata_json, dict) else None
                if not exec_id:
                    raise ValueError("No execution_id in conflict metadata")
                tasks_stmt = select(AgentTask).where(
                    AgentTask.tenant_id == tenant_id,
                    AgentTask.execution_reference == uuid.UUID(exec_id),
                    AgentTask.status != TaskStatus.COMPLETED,
                )
                result = await session.execute(tasks_stmt)
                for t in result.scalars():
                    t.status = TaskStatus.CANCELLED
                    t.completed_at = datetime.utcnow()
            elif strategy == "escalate":
                conflict.status = ConflictStatus.ESCALATED
            else:
                # Default – mark resolved
                conflict.status = ConflictStatus.RESOLVED

            # Record the chosen strategy and final status
            conflict.resolution_strategy = strategy
            conflict.status = ConflictStatus.RESOLVED if conflict.status != ConflictStatus.ESCALATED else ConflictStatus.ESCALATED

            await session.flush()
            # Metrics
            conflict_resolution_total.labels(tenant_id=str(tenant_id)).inc()
            # Audit entry
            entry = AuditLedgerEntry(
                tenant_id=tenant_id,
                action_name="conflict_resolved",
                actor_id=uuid.UUID(int=0),
                actor_type="system",
                target_type="conflict",
                target_id=conflict.id,
                summary=f"Conflict {conflict.id} resolved using {strategy}",
                input_snapshot={},
                output_snapshot={},
                decision=None,
                risk_level="low",
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()
            await session.commit()
            return conflict


# Export singleton service
conflict_resolution_service = ConflictResolutionService()
