"""
SEO Platform — Domain Models: Observability & Compliance
============================================================
Persistent tables for provider health metrics, audit trails,
campaign timeline events, and compliance scoring results.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ProviderHealthMetric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-call metrics for every external provider invocation."""

    __tablename__ = "provider_health_metrics"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    provider_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_healthy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    circuit_breaker_state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="CLOSED",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )


class AuditTrailLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent audit log for system events, fallbacks, and state changes."""

    __tablename__ = "audit_trail_logs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    execution_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )


class CampaignTimelineEvent(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Granular step-level progress tracking for campaign workflows."""

    __tablename__ = "campaign_timeline_events"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("backlink_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'pending'"),
    )
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    step_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )


class ComplianceResult(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Post-generation compliance scoring for AI-generated content."""

    __tablename__ = "compliance_results"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, default="email_pitch")
    banned_words_found: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    max_sentence_length_violated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, server_default=text("'{}'::jsonb"),
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )
