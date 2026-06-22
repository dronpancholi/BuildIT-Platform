"""
SEO Platform — Credential Vault Models
=======================================
SQLAlchemy models for encrypted credential storage and audit logging.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CredentialStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    LOCKED = "locked"
    EXPIRED = "expired"


class CredentialAuditAction(str, enum.Enum):
    CREATED = "created"
    USED = "used"
    SUCCESS = "success"
    FAILURE = "failure"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    ROTATED = "rotated"
    DELETED = "deleted"


class DirectoryCredential(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Encrypted credential storage for directory site accounts."""

    __tablename__ = "directory_credentials"

    # Site info
    site_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Credentials (encrypted)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_email: Mapped[str | None] = mapped_column(String(255))
    recovery_phone: Mapped[str | None] = mapped_column(String(50))

    # Status
    status: Mapped[str] = mapped_column(
        Enum("active", "suspended", "banned", "locked", "expired", name="credential_status"),
        default="active",
        server_default="active",
        nullable=False,
    )
    health_score: Mapped[int] = mapped_column(Integer, default=100, server_default="100")

    # Usage tracking
    use_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failure_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_reason: Mapped[str | None] = mapped_column(Text)

    # Rotation
    rotation_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotation_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    __table_args__ = (
        {"schema": None},
    )


class CredentialAuditLog(Base, UUIDPrimaryKeyMixin, TenantMixin):
    """Audit trail for all credential operations."""

    __tablename__ = "credential_audit_log"

    credential_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("directory_credentials.id", ondelete="SET NULL"),
        index=True,
    )
    action: Mapped[str] = mapped_column(
        Enum(
            "created", "used", "success", "failure", "locked",
            "unlocked", "rotated", "deleted",
            name="credential_audit_action",
        ),
        nullable=False,
    )
    site_slug: Mapped[str | None] = mapped_column(String(100))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
