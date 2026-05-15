"""
SEO Platform — SQLAlchemy Models: Base Mixins
===============================================
Shared model mixins providing tenant isolation, timestamps, and audit fields.

Design principles:
- Every table includes tenant_id (multi-tenancy from row 1)
- All timestamps are timezone-aware (TIMESTAMPTZ)
- UUID primary keys everywhere (no auto-increment integers for entity IDs)
- Audit fields (created_at, updated_at) on every mutable table
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds created_at and updated_at timestamps to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=text("NOW()"),
        nullable=True,
    )


class TenantMixin:
    """
    Adds tenant_id column for Row-Level Security isolation.

    Every model that contains tenant-specific data MUST inherit this mixin.
    RLS policies enforce filtering on tenant_id at the database level.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class UUIDPrimaryKeyMixin:
    """Adds UUID primary key with database-generated default."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
