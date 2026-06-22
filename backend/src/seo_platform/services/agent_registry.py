"""
SEO Platform — Phase 14 Service: Agent Registry
===================================================
Manages the lifecycle of AgentDefinition and AgentInstance records.
All operations are tenant‑scoped, audit‑logged, and emit Prometheus metrics.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Mapping, List

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.metrics import agent_count
from sqlalchemy import select
from sqlalchemy import inspect as sa_inspect
from seo_platform.models.agent import AgentDefinition, AgentInstance, AgentTask, AgentConflict
from seo_platform.models.audit_ledger import AuditLedgerEntry

logger = get_logger(__name__)

def _model_to_dict(instance: Any) -> dict[str, Any]:
    """Extract column data from a SQLAlchemy model instance, excluding internals."""
    result = {}
    for c in sa_inspect(instance).mapper.column_attrs:
        val = getattr(instance, c.key)
        if isinstance(val, uuid.UUID):
            val = str(val)
        result[c.key] = val
    return result

class AgentRegistryService:
    """Service for CRUD operations on agents and runtime updates."""

    async def create_agent(self, tenant_id: uuid.UUID, data: Mapping[str, Any]) -> AgentDefinition:
        async with get_tenant_session(tenant_id) as session:
            agent = AgentDefinition(tenant_id=tenant_id, **data)
            session.add(agent)
            await session.flush()
            await session.refresh(agent)
            await self._audit(
                tenant_id,
                "agent_create",
                f"Created agent {agent.name}",
                entity_type="agent_definition",
                entity_id=agent.id,
                actor_type="system",
                actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                input_snapshot=data,
                output_snapshot=_model_to_dict(agent),
            )
            # Update metric
            agent_count.labels(tenant_id=str(tenant_id)).inc()
            return agent

    async def update_agent(self, tenant_id: uuid.UUID, agent_id: uuid.UUID, data: Mapping[str, Any]) -> AgentDefinition:
        async with get_tenant_session(tenant_id) as session:
            agent = await session.get(AgentDefinition, agent_id)
            if not agent or agent.tenant_id != tenant_id:
                raise ValueError("Agent not found")
            before = _model_to_dict(agent)
            for key, value in data.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            await session.flush()
            await session.refresh(agent)
            await self._audit(
                tenant_id,
                "agent_update",
                f"Updated agent {agent.name}",
                entity_type="agent_definition",
                entity_id=agent.id,
                actor_type="system",
                actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                input_snapshot=before,
                output_snapshot=_model_to_dict(agent),
            )
            return agent

    async def disable_agent(self, tenant_id: uuid.UUID, agent_id: uuid.UUID) -> AgentDefinition:
        return await self.update_agent(tenant_id, agent_id, {"enabled": False})

    async def list_agents(self, tenant_id: uuid.UUID) -> List[AgentDefinition]:
        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(
                select(AgentDefinition).where(AgentDefinition.tenant_id == tenant_id)
            )
            return result.scalars().all()

    async def get_agent(self, tenant_id: uuid.UUID, agent_id: uuid.UUID) -> AgentDefinition | None:
        async with get_tenant_session(tenant_id) as session:
            agent = await session.get(AgentDefinition, agent_id)
            if agent and agent.tenant_id != tenant_id:
                return None
            return agent

    # Runtime state updates – health and workload
    async def update_health(self, tenant_id: uuid.UUID, instance_id: uuid.UUID, health_state: str) -> AgentInstance:
        async with get_tenant_session(tenant_id) as session:
            instance = await session.get(AgentInstance, instance_id)
            if not instance or instance.tenant_id != tenant_id:
                raise ValueError("Agent instance not found")
            instance.health_state = health_state
            await session.flush()
            await self._audit(
                tenant_id,
                "agent_health_update",
                f"Health set to {health_state} for instance {instance.id}",
                entity_type="agent_instance",
                entity_id=instance.id,
                actor_type="system",
                actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                input_snapshot={"health_state": health_state},
                output_snapshot=instance.__dict__,
            )
            return instance

    async def update_workload(self, tenant_id: uuid.UUID, instance_id: uuid.UUID, workload: list[uuid.UUID]) -> AgentInstance:
        async with get_tenant_session(tenant_id) as session:
            instance = await session.get(AgentInstance, instance_id)
            if not instance or instance.tenant_id != tenant_id:
                raise ValueError("Agent instance not found")
            instance.current_workload = workload
            await session.flush()
            await self._audit(
                tenant_id,
                "agent_workload_update",
                f"Workload updated for instance {instance.id}",
                entity_type="agent_instance",
                entity_id=instance.id,
                actor_type="system",
                actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                input_snapshot={"workload": workload},
                output_snapshot=instance.__dict__,
            )
            return instance

    async def _audit(
        self,
        tenant_id: uuid.UUID,
        action_name: str,
        summary: str,
        entity_type: str,
        entity_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        input_snapshot: dict[str, Any] | None = None,
        output_snapshot: dict[str, Any] | None = None,
    ) -> None:
        async with get_tenant_session(tenant_id) as session:
            entry = AuditLedgerEntry(
                tenant_id=tenant_id,
                action_name=action_name,
                action_execution_id=None,
                actor_id=uuid.UUID(str(actor_id)) if actor_id else uuid.UUID("00000000-0000-0000-0000-000000000000"),
                actor_type=actor_type,
                target_type=entity_type,
                target_id=entity_id,
                summary=summary,
                input_snapshot=input_snapshot or {},
                output_snapshot=output_snapshot or {},
                approval_id=None,
                decision=None,
                risk_level="low",
                ip_address=None,
                user_agent=None,
                semantic_hash="",
                rollback_id=None,
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()

# Export singleton
agent_registry = AgentRegistryService()
