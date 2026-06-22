"""
SEO Platform — Business Profile Model
======================================
Canonical business profile (NAP) separated from citation submission tracking.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base


class BusinessProfile(Base):
    """Canonical Business Profile (Single Source of Truth for NAP)."""

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
    phone_number: Mapped[str] = mapped_column(String(50))

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
