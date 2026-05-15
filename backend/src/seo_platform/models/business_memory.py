"""
SEO Platform — Domain Models: Business Memory
================================================
Persistent evolving business state for continuous intelligence.

These models store historical snapshots and trends so the platform
remembers and evolves its business intelligence over time.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
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


class CampaignHealthSnapshot(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Historical campaign health snapshot for trend analysis."""

    __tablename__ = "campaign_health_snapshots"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    health_score: Mapped[float] = mapped_column(Float, nullable=False)
    acquisition_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reply_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    momentum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )


class KeywordMetricSnapshot(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Historical keyword metric snapshot for ranking evolution."""

    __tablename__ = "keyword_metric_snapshots"

    keyword_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("keyword_clusters.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    search_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cpc: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ranking_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ranking_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    serp_features: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )


class SerpVolatilitySnapshot(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """SERP volatility and competitor movement tracking."""

    __tablename__ = "serp_volatility_snapshots"

    keyword: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    geo: Mapped[str] = mapped_column(String(10), nullable=False, default="us")
    volatility_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    url_churn: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position_changes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_changes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    top_10_domains: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )


class BusinessIntelligenceEvent(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Business intelligence events — real insights from workflows."""

    __tablename__ = "business_intelligence_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True,
    )
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    action_required: Mapped[bool] = mapped_column(
        "action_required", nullable=False, default=False,
    )
    acknowledged: Mapped[bool] = mapped_column(nullable=False, default=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )


class RecommendationModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Persistent recommendations with lifecycle tracking."""

    __tablename__ = "recommendations"

    recommendation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P2")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    effort_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True,
    )
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    supporting_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    implemented_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    effectiveness_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class ProspectScoreHistory(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Historical prospect scoring for trend analysis."""

    __tablename__ = "prospect_score_history"

    prospect_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_prospects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    domain_authority: Mapped[float] = mapped_column(Float, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    spam_score: Mapped[float] = mapped_column(Float, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    score_reason: Mapped[str] = mapped_column(String(100), nullable=False, default="scheduled_rescore")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"),
    )
