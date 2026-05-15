"""
SEO Platform — Keyword Research Models
==========================================
Store and retrieve AI-powered keyword research results.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    ForeignKey,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class KeywordResearch(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Result of an AI keyword research workflow."""

    __tablename__ = "keyword_research"

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    seed_keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    result_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    workflow_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
