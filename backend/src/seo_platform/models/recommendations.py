"""
SEO Platform — Recommendation Models
=====================================
SQLAlchemy models for smart site recommendations and competitor citations.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class RecommendationType(str, enum.Enum):
    LOCATION_MATCH = "location_match"
    INDUSTRY_MATCH = "industry_match"
    COMPETITOR_GAP = "competitor_gap"
    HIGH_AUTHORITY = "high_authority"
    TIER_MATCH = "tier_match"


class RecommendationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


# ---------------------------------------------------------------------------
# CitationRecommendation — Smart site recommendations per project
# ---------------------------------------------------------------------------
class CitationRecommendation(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """Intelligent site recommendations for a citation project."""

    __tablename__ = "citation_recommendations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citation_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citation_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Priority scoring (1-100)
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Recommendation type
    recommendation_type: Mapped[str] = mapped_column(
        Enum(
            "location_match",
            "industry_match",
            "competitor_gap",
            "high_authority",
            "tier_match",
            name="recommendation_type",
            create_type=False,
        ),
        nullable=False,
    )

    # Status
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "accepted",
            "rejected",
            "duplicate",
            name="recommendation_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'pending'"),
    )

    # Detailed scoring breakdown
    scoring_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Meta
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# CompetitorCitation — Track where competitors have citations
# ---------------------------------------------------------------------------
class CompetitorCitation(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """Tracks competitor citations for gap analysis."""

    __tablename__ = "competitor_citations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citation_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    competitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    competitor_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citation_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    site_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    citation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Citation quality signals
    has_images: Mapped[bool] = mapped_column(Boolean, default=False)
    has_complete_nap: Mapped[bool] = mapped_column(Boolean, default=False)
    citation_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # SEO signals
    domain_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Meta
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
