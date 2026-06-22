"""
SEO Platform — Phase 14 Models: Enterprise Audit Ledger
===================================================================
Append‑only immutable audit log for all autonomous actions, approvals,
and system‑level events. The table is partitioned by month via a
PostgreSQL trigger (defined elsewhere) and enforced as append‑only by a
trigger that raises an exception on UPDATE/DELETE.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin

# ---------------------------------------------------------------------------
# Enumerations for actor and decision types
# ---------------------------------------------------------------------------

class ActorType(str, enum.Enum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"

class DecisionType(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    ESCALATED = "escalated"
    BYPASSED = "bypassed"

# ---------------------------------------------------------------------------
# Audit Ledger Entry – append‑only log
# ---------------------------------------------------------------------------

class AuditLedgerEntry(Base, TenantMixin, TimestampMixin):
    """Immutable audit trail for every autonomous operation.

    Designed for compliance and forensic analysis. All writes go through the
    AuditLedgerService which inserts rows while the database trigger prevents any
    UPDATE or DELETE.
    """

    __tablename__ = "audit_ledger"
    __table_args__ = (
        Index("ix_audit_ledger_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_audit_ledger_action_created_at", "action_name", "created_at"),
        Index("ix_audit_ledger_actor_created_at", "actor_id", "created_at"),
        Index("ix_audit_ledger_target", "target_type", "target_id"),
    )

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )

    # Action information
    action_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("action_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Actor provenance
    actor_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Target of the action (entity acted upon)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Human‑readable summary
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Input / output snapshots for replayability & debugging
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    output_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # Approval context
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_requests_v2.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision: Mapped[DecisionType | None] = mapped_column(
        Enum(DecisionType, name="decision_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )

    # Risk & compliance metadata
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 safe
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Cryptographic integrity hash – SHA256 of tenant + exec id + timestamp
    semantic_hash: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'0'::text"))

    # Rollback reference (if any)
    rollback_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("action_executions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Immutable timestamp – captured once at insert time
    immutable_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLedgerEntry {self.id} action={self.action_name}>"
