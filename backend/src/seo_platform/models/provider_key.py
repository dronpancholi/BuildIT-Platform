"""
SEO Platform — ProviderKey Model
=================================
Persists provider API keys per tenant. Keys are encrypted at rest using the
platform's AES-256-GCM encryption service. Replaces the .env-only workflow
so operators can rotate keys at runtime without a service restart.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ProviderKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Stores an encrypted API key for a single (tenant, provider) pair.

    `encrypted_value` is the AES-256-GCM ciphertext (base64) emitted by
    `core.encryption.encryption_service.encrypt()`. The plaintext is never
    written to disk.

    For providers that need more than one credential (e.g. DataForSEO
    login + password, SendGrid api_key + sender_email) we store a JSON
    document so a single row covers the whole provider.
    """

    __tablename__ = "provider_keys"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_provider_keys_tenant_provider"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Stable provider identifier (e.g. 'dataforseo', 'hunter', 'sendgrid')",
    )

    encrypted_value: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
        doc="AES-256-GCM base64 ciphertext (nonce prepended)",
    )

    updated_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        doc="User id that last rotated this key (for audit)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        doc="Whether this provider key is enabled for use",
    )
