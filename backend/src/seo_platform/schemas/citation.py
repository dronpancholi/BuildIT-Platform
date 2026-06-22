"""
SEO Platform — Citation Automation Schemas
==========================================
Pydantic models for citation projects, sites, and submissions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Citation Site Schemas
# ---------------------------------------------------------------------------
class CitationSiteResponse(BaseModel):
    """Response schema for a citation site."""

    id: UUID
    name: str
    url: str
    submission_url: str | None = None
    registration_url: str | None = None
    category: str
    niche: str | None = None
    geo_target: str | None = None
    has_logo_upload: bool = False
    has_description: bool = True
    has_hours: bool = False
    has_social_links: bool = False
    has_images: bool = False
    has_video: bool = False
    requires_email_verification: bool = True
    difficulty_score: int = 50
    monthly_visitors: int = 0
    domain_authority: int = 30
    is_free: bool = True
    is_active: bool = True
    # Phase 6: Global expansion fields
    region: str | None = None
    importance_score: int = 50
    is_premium: bool = False
    monthly_audience: int | None = None
    language: str | None = "en"
    submission_difficulty: str | None = "medium"
    estimated_field_count: int = 15
    slug: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Citation Project Schemas
# ---------------------------------------------------------------------------
class CitationProjectCreate(BaseModel):
    """Request schema for creating a citation project."""

    business_name: str = Field(..., min_length=1, max_length=255)
    website_url: str | None = None
    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    phone: str | None = None
    email: str | None = None
    description: str | None = None
    short_bio: str | None = None
    long_bio: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = "Australia"
    postal_code: str | None = None
    hours_mon: str | None = None
    hours_tue: str | None = None
    hours_wed: str | None = None
    hours_thu: str | None = None
    hours_fri: str | None = None
    hours_sat: str | None = None
    hours_sun: str | None = None
    logo_url: str | None = None
    facebook_url: str | None = None
    twitter_url: str | None = None
    linkedin_url: str | None = None
    instagram_url: str | None = None
    youtube_url: str | None = None
    pinterest_url: str | None = None
    submission_email: str | None = None
    submission_password: str | None = None
    client_id: UUID | None = None

    @field_validator("website_url", "logo_url", "facebook_url", "twitter_url",
                     "linkedin_url", "instagram_url", "youtube_url", "pinterest_url",
                     mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> str | None:
        if v == "":
            return None
        return v


class CitationProjectUpdate(BaseModel):
    """Request schema for updating a citation project."""

    business_name: str | None = Field(None, min_length=1, max_length=255)
    website_url: str | None = None
    category: str | None = None
    keywords: list[str] | None = None
    phone: str | None = None
    email: str | None = None
    description: str | None = None
    short_bio: str | None = None
    long_bio: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    hours_mon: str | None = None
    hours_tue: str | None = None
    hours_wed: str | None = None
    hours_thu: str | None = None
    hours_fri: str | None = None
    hours_sat: str | None = None
    hours_sun: str | None = None
    logo_url: str | None = None
    facebook_url: str | None = None
    twitter_url: str | None = None
    linkedin_url: str | None = None
    instagram_url: str | None = None
    youtube_url: str | None = None
    pinterest_url: str | None = None
    submission_email: str | None = None
    submission_password: str | None = None
    client_id: UUID | None = None


class CitationProjectStats(BaseModel):
    """Computed stats for a citation project."""

    total_sites: int = 0
    pending: int = 0
    in_progress: int = 0
    already_exists: int = 0
    new_backlink: int = 0
    failed: int = 0
    rejected: int = 0
    completion_pct: float = 0.0


class CitationProjectResponse(BaseModel):
    """Response schema for a citation project."""

    id: UUID
    tenant_id: UUID
    client_id: UUID | None = None
    business_name: str
    website_url: str | None = None
    category: str | None = None
    keywords: list[str] | None = None
    phone: str | None = None
    email: str | None = None
    description: str | None = None
    short_bio: str | None = None
    long_bio: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    hours_mon: str | None = None
    hours_tue: str | None = None
    hours_wed: str | None = None
    hours_thu: str | None = None
    hours_fri: str | None = None
    hours_sat: str | None = None
    hours_sun: str | None = None
    logo_url: str | None = None
    facebook_url: str | None = None
    twitter_url: str | None = None
    linkedin_url: str | None = None
    instagram_url: str | None = None
    youtube_url: str | None = None
    pinterest_url: str | None = None
    submission_email: str | None = None
    status: str = "active"
    total_sites: int = 0
    pending_count: int = 0
    in_progress_count: int = 0
    already_exists_count: int = 0
    new_backlink_count: int = 0
    failed_count: int = 0
    stats: CitationProjectStats | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Citation Submission Schemas
# ---------------------------------------------------------------------------
class SubmissionCreate(BaseModel):
    """Request schema for creating a submission entry."""

    site_id: UUID
    status: str = "not_started"
    notes: str | None = None


class SubmissionBulkCreate(BaseModel):
    """Request schema for bulk-creating submissions."""

    site_ids: list[UUID] = Field(..., min_length=1)
    status: str = "not_started"


class SubmissionStatusUpdate(BaseModel):
    """Request schema for updating a submission status."""

    status: str = Field(..., description="New status value")
    status_notes: str | None = None
    listing_url: str | None = None
    account_created: bool | None = None
    email_verified: bool | None = None
    listing_claimed: bool | None = None
    notes: str | None = None


class SubmissionUpdate(BaseModel):
    """Request schema for updating submission details."""

    status: str | None = None
    status_notes: str | None = None
    listing_url: str | None = None
    account_created: bool | None = None
    email_verified: bool | None = None
    listing_claimed: bool | None = None
    notes: str | None = None
    form_data: dict[str, Any] | None = None


class SubmissionResponse(BaseModel):
    """Response schema for a citation submission."""

    id: UUID
    project_id: UUID
    site_id: UUID
    site_name: str | None = None
    site_url: str | None = None
    site_category: str | None = None
    site_difficulty: int | None = None
    site_da: int | None = None
    status: str = "not_started"
    status_notes: str | None = None
    account_created: bool = False
    email_verified: bool = False
    listing_claimed: bool = False
    listing_url: str | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Discovery Schema
# ---------------------------------------------------------------------------
class DiscoveryResult(BaseModel):
    """Result of site discovery for a project."""

    sites_added: int = 0
    sites_already_tracked: int = 0
    total_available: int = 0
