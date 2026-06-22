"""
SEO Platform — Phase 14 Models: Agent Orchestration
===================================================================
Defines the core data structures for autonomous agents, their instances,
assigned tasks, and conflict tracking.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (DateTime,
    Boolean,
    Column,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enums for agent state and task status
# ---------------------------------------------------------------------------

class AgentRunningState(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"

class AgentHealthState(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ConflictStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

# ---------------------------------------------------------------------------
# Agent Definition – static catalog of agent capabilities
# ---------------------------------------------------------------------------

class AgentDefinition(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "agent_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_agent_def_tenant_name"),
        Index("ix_agent_def_tenant_enabled", "tenant_id", "enabled"),
        {"extend_existing": True},
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # Relationships
    instances: Mapped[list["AgentInstance"]] = relationship(
        "AgentInstance", back_populates="definition", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<AgentDefinition {self.tenant_id}:{self.name}>"

# ---------------------------------------------------------------------------
# Agent Instance – runtime representation of a running agent
# ---------------------------------------------------------------------------

class AgentInstance(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "agent_instances"
    # Allow redefinition if module is re‑imported during testing
    __table_args__ = (
        Index("ix_agent_instances_definition_status", "definition_id", "running_state"),
        {"extend_existing": True},
    )


    definition_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    running_state: Mapped[AgentRunningState] = mapped_column(
        Enum(AgentRunningState, name="agent_running_state", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=text("'idle'"),
    )
    health_state: Mapped[AgentHealthState] = mapped_column(
        Enum(AgentHealthState, name="agent_health_state", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=text("'healthy'"),
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Execution counters – JSON blob for extensibility (e.g., tasks_executed, failures)
    execution_counters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    # Current workload description – list of Task IDs
    current_workload: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), nullable=True)
    # Memory references – list of MemoryEntry IDs for this instance
    memory_refs: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), nullable=True)

    definition: Mapped[AgentDefinition] = relationship("AgentDefinition", back_populates="instances", lazy="joined")
    tasks: Mapped[list["AgentTask"]] = relationship("AgentTask", back_populates="agent_instance", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AgentInstance {self.id} state={self.running_state}>"

# ---------------------------------------------------------------------------
# Agent Task – a unit of work assigned to an agent instance
# ---------------------------------------------------------------------------

class AgentTask(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        Index("ix_agent_task_tenant_status", "tenant_id", "status"),
        Index("ix_agent_task_priority", "priority"),
        Index("ix_agent_task_created", "created_at"),
        {"extend_existing": True},
    )

    agent_instance_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="agent_task_status", native_enum=False, create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=text("'pending'"),
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    urgency: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # References to higher‑level plan or execution (optional)
    plan_reference: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    execution_reference: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("action_executions.id", ondelete="SET NULL"), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    agent_instance: Mapped[AgentInstance] = relationship("AgentInstance", back_populates="tasks", lazy="joined")
    execution: Mapped["ActionExecution | None"] = relationship("ActionExecution", lazy="joined")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AgentTask {self.id} status={self.status}>"

# ---------------------------------------------------------------------------
# Agent Conflict – records detected conflicts between agents/tasks
# ---------------------------------------------------------------------------

class AgentConflict(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "agent_conflicts"
    __table_args__ = (
        Index("ix_agent_conflict_tenant_status", "tenant_id", "status"),
    )

    conflict_type: Mapped[str] = mapped_column(String(100), nullable=False)
    involved_agents: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), nullable=False)
    resolution_strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ConflictStatus] = mapped_column(
        Enum(ConflictStatus, name="conflict_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=text("'open'"),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    def __repr__(self) -> str:
        return f"<AgentConflict {self.id} type={self.conflict_type} status={self.status}>"

