"""
SEO Platform — Phase 14 Models: Approval Policy & Request
===================================================================
Defines policy objects used by the Human Approval System and the
runtime approval requests that gate action executions.
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
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

# ---------------------------------------------------------------------------
# Approval Policy – static governance configuration per tenant
# ---------------------------------------------------------------------------

class ApprovalPolicy(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Governance policy determining when and how approvals are required.

    Policies can be scoped to a specific action category or apply globally.
    """

    __tablename__ = "approval_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_approval_policy_name"),
        Index("ix_approval_policy_tenant_active", "tenant_id", "is_active"),
    )

    # Core identifiers
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification & scope
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="policy_risk_level", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    action_category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. "campaign", null = all

    # Approval workflow details
    requires_chain: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    chain_order: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)  # ordered list of role names or user IDs
    timeout_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("48"))
    escalation_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    auto_approve_if_no_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    requires_justification: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    min_approvers: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))

    def __repr__(self) -> str:
        return f"<ApprovalPolicy {self.tenant_id}:{self.name}>"

# ---------------------------------------------------------------------------
# Approval Request – runtime instance of an approval workflow
# ---------------------------------------------------------------------------

class ApprovalRequest(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Instance of a pending/processed approval request.

    Linked to an ``ActionExecution`` and governed by an ``ApprovalPolicy``.
    """

    __tablename__ = "approval_requests_v2"
    __table_args__ = (
        Index("ix_approval_req_tenant_status_created", "tenant_id", "status", "created_at"),
        Index("ix_approval_req_tenant_current_approver", "tenant_id", "current_approver_role", "status"),
    )

    # Links
    policy_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("action_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    # State machine
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=text("'pending'"),
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="approval_risk_level", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Human‑readable context
    action_summary: Mapped[str] = mapped_column(Text, nullable=False)
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    current_approver_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    approval_chain: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)  # full chain configuration snapshot
    approval_history: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)  # array of {approver_id, role, decision, comment, timestamp}

    # Timing
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ApprovalRequest {self.id} status={self.status}>"
