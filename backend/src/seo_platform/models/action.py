"""
SEO Platform — Phase 14 Models: Action Registry
================================================
Defines the catalog of executable actions (ActionDefinition) and the
runtime execution log (ActionExecution).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seo_platform.core.database import Base
from seo_platform.models.base import UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ActionCategory(str, enum.Enum):
    CRM = "crm"
    CAMPAIGN = "campaign"
    COMMUNICATION = "communication"
    ANALYTICS = "analytics"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"

# ---------------------------------------------------------------------------
# Action Definition – static catalog of actions available to tenants
# ---------------------------------------------------------------------------

class ActionDefinition(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Static definition of an executable action.

    Each tenant can define its own actions, inheriting the same schema. The
    ``name`` field is unique per tenant to allow easy lookup.
    """

    __tablename__ = "action_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_action_def_tenant_name"),
        Index("ix_action_def_tenant_category", "tenant_id", "category"),
    )

    # Core identifiers
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification
    category: Mapped[ActionCategory] = mapped_column(
        Enum(ActionCategory, name="action_category", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="action_risk_level", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Schemas – JSON descriptors of expected input/outout
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Security & governance
    permission_required: Mapped[str] = mapped_column(String(100), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    approval_policy: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Execution configuration
    rollback_handler: Mapped[str | None] = mapped_column(String(255), nullable=True)
    execution_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("300"))
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    idempotent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    custom_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    executions: Mapped[list["ActionExecution"]] = relationship(
        "ActionExecution",
        back_populates="definition",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ActionDefinition {self.tenant_id}:{self.name}>"

# ---------------------------------------------------------------------------
# Action Execution – runtime instance of an action
# ---------------------------------------------------------------------------

class ActionExecution(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Runtime record of an action execution.

    The lifecycle is expressed through ``status`` and transitions are
    orchestrated by the ExecutionEngine service.
    """

    __tablename__ = "action_executions"
    __table_args__ = (
        Index("ix_action_exec_tenant_status", "tenant_id", "status"),
        Index("ix_action_exec_definition", "definition_id"),
        Index("ix_action_exec_idempotency", "tenant_id", "idempotency_key", unique=True),
        Index("ix_action_exec_parent", "parent_execution_id"),
    )

    # Link to definition
    definition_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("action_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Execution state machine
    status: Mapped[ActionExecutionStatus] = mapped_column(
        Enum(ActionExecutionStatus, name="action_execution_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=text("'pending'"),
    )

    # Payloads
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Human approval linkage
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_request_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_requests_v2.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Correlation & hierarchy
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    parent_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("action_executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    execution_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    definition: Mapped[ActionDefinition] = relationship("ActionDefinition", back_populates="executions", lazy="joined")
    parent_execution: Mapped["ActionExecution | None"] = relationship(
        "ActionExecution",
        remote_side="ActionExecution.id",
        backref="child_executions",
        lazy="joined",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<ActionExecution {self.id} status={self.status}>"
