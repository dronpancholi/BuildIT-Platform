"""
SEO Platform — Phase 14 Models: Goal Orchestration
===================================================================
Defines GoalDefinition and GoalExecution for orchestrating autonomous business objectives.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    DateTime,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Goal state enum
# ---------------------------------------------------------------------------

class GoalState(str, enum.Enum):
    NEW = "new"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# ---------------------------------------------------------------------------
# Goal Definition – static description of a business objective
# ---------------------------------------------------------------------------

class GoalDefinition(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "goal_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_goal_def_tenant_name"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Target can be arbitrary JSON (e.g., revenue increase, KPI list)
    target: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    # Relationships – executions of this goal
    executions: Mapped[list["GoalExecution"]] = relationship(
        "GoalExecution", back_populates="definition", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<GoalDefinition {self.tenant_id}:{self.name}>"

# ---------------------------------------------------------------------------
# Goal Execution – runtime instance of a goal being pursued
# ---------------------------------------------------------------------------

class GoalExecution(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "goal_executions"
    __table_args__ = (
        Index("ix_goal_execution_tenant_state", "tenant_id", "state"),
    )

    definition_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("goal_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[GoalState] = mapped_column(
        Enum(GoalState, name="goal_state", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=text("'new'"),
    )
    # Optional summary of execution outcome
    outcome_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    definition: Mapped[GoalDefinition] = relationship("GoalDefinition", back_populates="executions", lazy="joined")

    def __repr__(self) -> str:
        return f"<GoalExecution {self.id} state={self.state}>"
