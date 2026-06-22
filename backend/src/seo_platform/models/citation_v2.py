"""
SEO Platform — Citation Automation Models (v2)
=============================================
SQLAlchemy models for the citation tracking schema:
  - CitationSite: Master list of citation/directory sites
  - CitationProject: Per-business citation campaign
  - CitationSubmissionV2: Per-site submission tracking

These map to the tables created by citation_schema.sql and tracked
by Alembic migration j1_add_citation_tables.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class CitationProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CitationStatus(str, enum.Enum):
    PENDING = "pending"
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ALREADY_EXISTS = "already_exists"
    NEW_BACKLINK = "new_backlink"
    PENDING_REVIEW = "pending_review"
    FAILED = "failed"
    REJECTED = "rejected"


class CitationCategory(str, enum.Enum):
    GENERAL = "general"
    LOCAL = "local"
    BUSINESS = "business"
    SOCIAL = "social"
    REVIEW = "review"
    DIRECTORY = "directory"
    NICHE = "niche"
    GOVERNMENT = "government"
    EDUCATION = "education"


# ---------------------------------------------------------------------------
# CitationSite — Master list of citation/directory sites
# ---------------------------------------------------------------------------
class CitationSite(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """Master list of citation and business directory sites."""

    __tablename__ = "citation_sites"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    submission_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    registration_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="'general'"
    )
    niche: Mapped[str | None] = mapped_column(String(255), nullable=True)
    geo_target: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Capability flags
    has_logo_upload: Mapped[bool] = mapped_column(Boolean, default=False)
    has_description: Mapped[bool] = mapped_column(Boolean, default=True)
    has_hours: Mapped[bool] = mapped_column(Boolean, default=False)
    has_social_links: Mapped[bool] = mapped_column(Boolean, default=False)
    has_images: Mapped[bool] = mapped_column(Boolean, default=False)
    has_video: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_email_verification: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metrics
    difficulty_score: Mapped[int] = mapped_column(Integer, default=50)
    monthly_visitors: Mapped[int] = mapped_column(Integer, default=0)
    domain_authority: Mapped[int] = mapped_column(Integer, default=30)

    # Flags
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Phase 6: Global expansion fields
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    importance_score: Mapped[int] = mapped_column(Integer, default=50)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    monthly_audience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), server_default="en")
    submission_difficulty: Mapped[str | None] = mapped_column(String(20), server_default="medium")
    estimated_field_count: Mapped[int] = mapped_column(Integer, default=15)
    slug: Mapped[str | None] = mapped_column(String(255), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# CitationProject — Per-business citation campaign
# ---------------------------------------------------------------------------
class CitationProject(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """A citation project tracks all directory submissions for one business."""

    __tablename__ = "citation_projects"

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # Contact
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Address
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), default="Australia")
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)

    # Operating hours
    hours_mon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hours_tue: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hours_wed: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hours_thu: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hours_fri: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hours_sat: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hours_sun: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Media
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    images: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=list)

    # Social
    facebook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pinterest_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Submission credentials (encrypted at application level)
    submission_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submission_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status & counters
    status: Mapped[str] = mapped_column(
        ENUM(
            "active",
            "paused",
            "completed",
            "archived",
            name="citation_project_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'active'"),
    )
    total_sites: Mapped[int] = mapped_column(Integer, default=0)
    pending_count: Mapped[int] = mapped_column(Integer, default=0)
    in_progress_count: Mapped[int] = mapped_column(Integer, default=0)
    already_exists_count: Mapped[int] = mapped_column(Integer, default=0)
    new_backlink_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------------------
# CitationSubmissionV2 — Per-site submission tracking
# ---------------------------------------------------------------------------
class CitationSubmissionV2(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """Tracks an individual citation submission to a specific directory."""

    __tablename__ = "citation_submissions"

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

    status: Mapped[str] = mapped_column(
        ENUM(
            "pending",
            "not_started",
            "in_progress",
            "already_exists",
            "new_backlink",
            "pending_review",
            "failed",
            "rejected",
            name="citation_status",
            create_type=False,
        ),
        nullable=False,
        server_default=text("'not_started'"),
    )
    status_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification flags
    account_created: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    listing_claimed: Mapped[bool] = mapped_column(Boolean, default=False)

    listing_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    form_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        {"extend_existing": True},
    )
