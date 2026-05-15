"""
SEO Platform — Citation & Local Listing Models
===============================================
SQLAlchemy models for the Local Citation & Business Listing Engine.
Ensures deterministic tracking of NAP profiles, directory submissions,
and listing verifications.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base


class VerificationState(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    LIVE = "live"
    REMOVED = "removed"
    DUPLICATE = "duplicate"
    INCONSISTENT = "inconsistent"

class BusinessProfile(Base):
    """
    Canonical Business Profile (The Single Source of Truth).
    Contains strictly normalized NAP (Name, Address, Phone) data.
    """
    __tablename__ = "business_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)

    # NAP Core
    business_name: Mapped[str] = mapped_column(String(255))
    street_address: Mapped[str] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(100))
    state_province: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(20))
    country_code: Mapped[str] = mapped_column(String(2))
    phone_number: Mapped[str] = mapped_column(String(50)) # E.164 normalized

    # Extended Profile
    website_url: Mapped[str] = mapped_column(String(255))
    primary_category: Mapped[str] = mapped_column(String(100))
    secondary_categories: Mapped[list[str]] = mapped_column(JSONB, default=list)
    description: Mapped[str] = mapped_column(String(2000))

    # Geolocation
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class CitationSubmission(Base):
    """
    Tracks an individual submission to a specific directory adapter.
    """
    __tablename__ = "citation_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True)
    workflow_run_id: Mapped[str] = mapped_column(String(255), index=True)

    directory_adapter: Mapped[str] = mapped_column(String(100)) # e.g., "yellowpages", "justdial"
    submission_status: Mapped[str] = mapped_column(String(50), default="queued") # queued, processing, submitted, failed
    submission_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Verification State
    verification_state: Mapped[str] = mapped_column(String(50), default=VerificationState.PENDING.value)
    live_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    nap_consistency_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Operational Observability
    automation_trace_url: Mapped[str | None] = mapped_column(String(500), nullable=True) # Playwright trace URL
    screenshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
