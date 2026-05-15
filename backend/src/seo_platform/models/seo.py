"""
SEO Platform — Domain Models: SEO Intelligence
=================================================
Keywords, clusters, SERP snapshots, and intent classification.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SearchIntent(str, enum.Enum):
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"


class ClusterStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Keyword(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Individual keyword with enrichment data from DataForSEO."""

    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", "keyword", name="uq_keyword_tenant_client"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("keyword_clusters.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    search_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cpc: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    competition: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    intent: Mapped[SearchIntent | None] = mapped_column(
        Enum(SearchIntent, name="search_intent", create_constraint=True, values_callable=lambda x: [e.value for e in x]), nullable=True,
    )
    serp_features: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    enrichment_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    is_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding_vector_id: Mapped[str | None] = mapped_column(String(255), nullable=True)


class KeywordCluster(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Cluster of semantically related keywords (HDBSCAN + NIM embeddings)."""

    __tablename__ = "keyword_clusters"

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    total_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dominant_intent: Mapped[SearchIntent | None] = mapped_column(
        Enum(SearchIntent, name="search_intent", create_constraint=True, create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    keyword_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[ClusterStatus] = mapped_column(
        Enum(ClusterStatus, name="cluster_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=ClusterStatus.DRAFT,
    )
    ai_rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )

    # Relationships
    keywords: Mapped[list[Keyword]] = relationship(
        "Keyword", backref="cluster", lazy="selectin",
        foreign_keys=[Keyword.cluster_id],
    )


class ReportModel(Base, UUIDPrimaryKeyMixin, TenantMixin):
    """Generated reports with AI summaries."""

    __tablename__ = "reports"

    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_campaigns.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    ai_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
