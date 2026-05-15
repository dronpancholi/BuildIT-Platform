"""
SEO Platform — Domain Models: Approval System
================================================
Human-in-the-loop approval requests, decisions, and escalation.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seo_platform.models.tenant import Tenant

from sqlalchemy import (
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ApprovalStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATION_REQUESTED = "modification_requested"
    EXPIRED = "expired"
    DELEGATED = "delegated"


class RiskLevelEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalCategory(str, enum.Enum):
    CAMPAIGN_LAUNCH = "campaign_launch"
    OUTREACH_TEMPLATES = "outreach_templates"
    KEYWORD_CLUSTERS = "keyword_clusters"
    PROSPECT_LIST = "prospect_list"
    BUDGET_OVERRIDE = "budget_override"
    RULE_CHANGE = "rule_change"


class ApprovalRequestModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Approval request awaiting human decision."""

    __tablename__ = "approval_requests"

    workflow_run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[ApprovalCategory] = mapped_column(
        Enum(ApprovalCategory, name="approval_category", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True,
    )
    risk_level: Mapped[RiskLevelEnum] = mapped_column(
        Enum(RiskLevelEnum, name="risk_level", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True,
    )
    status: Mapped[ApprovalStatusEnum] = mapped_column(
        Enum(ApprovalStatusEnum, name="approval_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=ApprovalStatusEnum.PENDING, index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    ai_risk_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    modifications: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    escalation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", lazy="selectin")
