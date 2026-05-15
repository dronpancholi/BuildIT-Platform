"""
SEO Platform — Domain Models: Backlink Engine
================================================
Campaigns, prospects, outreach threads, and link verification.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seo_platform.models.tenant import Client, Tenant

from sqlalchemy import (
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    PROSPECTING = "prospecting"
    SCORING = "scoring"
    OUTREACH_PREP = "outreach_prep"
    AWAITING_APPROVAL = "awaiting_approval"
    ACTIVE = "active"
    PAUSED = "paused"
    MONITORING = "monitoring"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class CampaignType(str, enum.Enum):
    GUEST_POST = "guest_post"
    RESOURCE_PAGE = "resource_page"
    NICHE_EDIT = "niche_edit"
    BROKEN_LINK = "broken_link"
    SKYSCRAPER = "skyscraper"
    HARO = "haro"


class ProspectStatus(str, enum.Enum):
    NEW = "new"
    SCORED = "scored"
    APPROVED = "approved"
    REJECTED = "rejected"
    OUTREACH_QUEUED = "outreach_queued"
    CONTACTED = "contacted"
    REPLIED = "replied"
    LINK_ACQUIRED = "link_acquired"
    LINK_LOST = "link_lost"
    UNRESPONSIVE = "unresponsive"


class ThreadStatus(str, enum.Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"
    SPAM_REPORTED = "spam_reported"
    UNSUBSCRIBED = "unsubscribed"
    LINK_ACQUIRED = "link_acquired"


class LinkStatus(str, enum.Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED_LIVE = "verified_live"
    VERIFIED_NOFOLLOW = "verified_nofollow"
    REMOVED = "removed"
    BROKEN = "broken"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class BacklinkCampaign(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Backlink acquisition campaign with state machine lifecycle."""

    __tablename__ = "backlink_campaigns"

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_type: Mapped[CampaignType] = mapped_column(
        Enum(CampaignType, name="campaign_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]), nullable=False,
    )
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=CampaignStatus.DRAFT, index=True,
    )
    target_link_count: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    acquired_link_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_prospects: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_emails_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reply_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    acquisition_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    health_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    workflow_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", lazy="selectin")

    # Relationships
    client: Mapped[Client] = relationship("Client", lazy="selectin")
    prospects: Mapped[list[BacklinkProspect]] = relationship(
        "BacklinkProspect", back_populates="campaign", lazy="dynamic",
    )


class BacklinkProspect(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Website identified as a potential backlink source."""

    __tablename__ = "backlink_prospects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "campaign_id", "domain", name="uq_prospect_campaign_domain"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[ProspectStatus] = mapped_column(
        Enum(ProspectStatus, name="prospect_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=ProspectStatus.NEW, index=True,
    )

    # Scoring signals
    domain_authority: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    spam_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    traffic_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Contact info
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # hunter, snov, manual

    scoring_rationale: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    page_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )

    # Relationships
    campaign: Mapped[BacklinkCampaign] = relationship("BacklinkCampaign", back_populates="prospects")
    threads: Mapped[list[OutreachThread]] = relationship("OutreachThread", back_populates="prospect", lazy="selectin")


class OutreachThread(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Email outreach thread to a prospect (1 initial + N follow-ups)."""

    __tablename__ = "outreach_threads"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    prospect_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_prospects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[ThreadStatus] = mapped_column(
        Enum(ThreadStatus, name="thread_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=ThreadStatus.DRAFT, index=True,
    )
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    follow_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_follow_ups: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="sendgrid")
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ai_personalization: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )

    # Relationships
    prospect: Mapped[BacklinkProspect] = relationship("BacklinkProspect", back_populates="threads")


class AcquiredLink(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Verified backlink acquisition record."""

    __tablename__ = "acquired_links"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    prospect_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("backlink_prospects.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    anchor_text: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    link_type: Mapped[str] = mapped_column(String(50), nullable=False, default="dofollow")
    status: Mapped[LinkStatus] = mapped_column(
        Enum(LinkStatus, name="link_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=LinkStatus.PENDING_VERIFICATION,
    )
    domain_authority_at_acquisition: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    first_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
