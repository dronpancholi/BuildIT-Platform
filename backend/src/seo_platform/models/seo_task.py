"""
SEO Task Model — Unified task management for operators.
Every recommendation, citation failure, outreach action becomes a trackable task.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TaskStatus(str, enum.Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TaskSource(str, enum.Enum):
    MANUAL = "manual"
    RECOMMENDATION = "recommendation"
    CITATION_FAILURE = "citation_failure"
    OUTREACH_ACTION = "outreach_action"
    CAMPAIGN_HEALTH = "campaign_health"
    AUTOMATION = "automation"
    COPILOT = "copilot"


class SEOTask(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Unified task management for operators."""

    __tablename__ = "seo_tasks"

    # Task content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=TaskStatus.CREATED,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=TaskPriority.P1,
    )
    source: Mapped[TaskSource] = mapped_column(
        Enum(TaskSource, name="task_source", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=TaskSource.MANUAL,
    )

    # Relationships
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_campaigns.id"), nullable=True, index=True,
    )

    # Assignment
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Source reference
    source_recommendation_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # Impact tracking
    impact_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Due date
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Outcome
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    extra_data: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        Index("ix_seo_tasks_tenant_status", "tenant_id", "status"),
        Index("ix_seo_tasks_tenant_priority", "tenant_id", "priority"),
        Index("ix_seo_tasks_tenant_client", "tenant_id", "client_id"),
        Index("ix_seo_tasks_tenant_campaign", "tenant_id", "campaign_id"),
    )
