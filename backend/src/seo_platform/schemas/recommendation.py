"""
SEO Platform — Recommendation Schemas
======================================
Pydantic models for site recommendations and competitor analysis API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Recommendation Schemas
# ---------------------------------------------------------------------------
class ScoringBreakdown(BaseModel):
    """Detailed scoring breakdown for a recommendation."""

    location_score: int = Field(0, ge=0, le=100)
    authority_score: int = Field(0, ge=0, le=100)
    industry_score: int = Field(0, ge=0, le=100)
    competitor_score: int = Field(0, ge=0, le=100)
    tier_score: int = Field(0, ge=0, le=100)


class RecommendationResponse(BaseModel):
    """Response schema for a site recommendation."""

    id: UUID
    project_id: UUID
    site_id: UUID
    site_name: str | None = None
    site_url: str | None = None
    site_category: str | None = None
    site_importance: int | None = None
    site_region: str | None = None
    site_difficulty: str | None = None

    priority_score: int
    priority_reason: str | None = None
    recommendation_type: str
    status: str = "pending"
    scoring_breakdown: ScoringBreakdown | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class RecommendationSummary(BaseModel):
    """Summary of recommendations for a project."""

    total: int = 0
    pending: int = 0
    accepted: int = 0
    rejected: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class GenerateRecommendationsRequest(BaseModel):
    """Request to generate recommendations for a project."""

    competitor_domains: list[str] = Field(default_factory=list)
    max_results: int = Field(50, ge=1, le=200)
    force_regenerate: bool = False


class BulkAcceptRequest(BaseModel):
    """Request to accept multiple recommendations."""

    recommendation_ids: list[UUID] = Field(..., min_length=1)


class UpdateRecommendationRequest(BaseModel):
    """Request to update a recommendation status."""

    status: str = Field(..., description="New status: accepted, rejected")
    notes: str | None = None


# ---------------------------------------------------------------------------
# Competitor Schemas
# ---------------------------------------------------------------------------
class CompetitorCreate(BaseModel):
    """Request to add a competitor."""

    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)


class CompetitorBulkCreate(BaseModel):
    """Request to add multiple competitors."""

    competitors: list[CompetitorCreate] = Field(..., min_length=1)


class CompetitorResponse(BaseModel):
    """Response schema for a competitor citation entry."""

    id: UUID
    project_id: UUID
    competitor_name: str
    competitor_domain: str | None = None
    site_id: UUID | None = None
    site_name: str | None = None
    site_url: str | None = None
    citation_url: str | None = None
    has_images: bool = False
    has_complete_nap: bool = False
    citation_age_months: int | None = None
    domain_rating: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class GapAnalysisResponse(BaseModel):
    """Gap analysis showing competitor-only sites."""

    site_id: UUID
    site_name: str
    site_url: str
    site_importance: int | None = None
    competitor_count: int = 0
    competitor_names: list[str] = Field(default_factory=list)
    is_client_listed: bool = False


class RecommendationStats(BaseModel):
    """Stats about recommendations for a project."""

    total_sites: int = 0
    recommended_count: int = 0
    accepted_count: int = 0
    already_submitted: int = 0
    competitor_sites: int = 0
    avg_priority: float = 0.0
