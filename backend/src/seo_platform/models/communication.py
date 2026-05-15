"""
SEO Platform — Communication Models
=====================================
Track email delivery status, bounces, and responses.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, UUIDPrimaryKeyMixin


class EmailStatus(str, enum.Enum):
    """Email delivery status."""
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    OPENED = "opened"
    REPLIED = "replied"
    FAILED = "failed"


class OutreachEmail(Base, UUIDPrimaryKeyMixin, TenantMixin):
    """
    Tracks individual outreach emails with delivery status.
    Enables communication reliability and analytics.
    """

    __tablename__ = "outreach_emails"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    prospect_id: Mapped[str] = mapped_column(String(255), nullable=False)

    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to_name: Mapped[str] = mapped_column(String(255), nullable=True)

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus, name="email_status", create_constraint=True),
        nullable=False, default=EmailStatus.QUEUED,
    )

    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=True)
    provider_response: Mapped[dict] = mapped_column(JSONB, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    failure_reason: Mapped[str] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)

    response_content: Mapped[dict] = mapped_column(JSONB, nullable=True)


class EmailTemplate(Base, UUIDPrimaryKeyMixin, TenantMixin):
    """
    Reusable email templates for outreach campaigns.
    """

    __tablename__ = "email_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_template: Mapped[str] = mapped_column(String(500), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)

    template_type: Mapped[str] = mapped_column(String(50), nullable=False)

    variables: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(default=True)

    usage_count: Mapped[int] = mapped_column(default=0)
    success_rate: Mapped[float] = mapped_column(default=0.0)
