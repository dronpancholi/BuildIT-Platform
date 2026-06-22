"""
SEO Platform — Smart Site Recommender Service
===============================================
Multi-signal scoring engine for intelligent citation site recommendations.

Scoring weights by tier:
- Starter:      authority=40, location=30, competitor=20, industry=10
- Professional: authority=30, competitor=30, location=25, industry=15
- Enterprise:   competitor=40, authority=30, industry=20, location=10
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.logging import get_logger
from seo_platform.models.citation_v2 import CitationProject, CitationSite, CitationSubmissionV2
from seo_platform.models.recommendations import (
    CitationRecommendation,
    CompetitorCitation,
)

logger = get_logger(__name__)

# Scoring weights per tier
TIER_WEIGHTS: dict[str, dict[str, float]] = {
    "starter": {"authority": 0.40, "location": 0.30, "competitor": 0.20, "industry": 0.10},
    "professional": {"authority": 0.30, "competitor": 0.30, "location": 0.25, "industry": 0.15},
    "enterprise": {"competitor": 0.40, "authority": 0.30, "industry": 0.20, "location": 0.10},
}

# Country to region mapping
COUNTRY_TO_REGION: dict[str, str] = {
    "australia": "AU",
    "au": "AU",
    "united states": "US",
    "us": "US",
    "usa": "US",
    "united kingdom": "UK",
    "uk": "UK",
    "canada": "CA",
    "ca": "CA",
    "germany": "EU",
    "de": "EU",
    "france": "EU",
    "fr": "EU",
    "netherlands": "EU",
    "nl": "EU",
    "spain": "EU",
    "es": "EU",
    "italy": "EU",
    "it": "EU",
    "poland": "EU",
    "pl": "EU",
    "sweden": "EU",
    "se": "EU",
    "belgium": "EU",
    "be": "EU",
    "austria": "EU",
    "at": "EU",
    "switzerland": "EU",
    "ch": "EU",
    "portugal": "EU",
    "pt": "EU",
    "european union": "EU",
    "eu": "EU",
    "india": "APAC",
    "in": "APAC",
    "japan": "APAC",
    "jp": "APAC",
    "south korea": "APAC",
    "kr": "APAC",
    "singapore": "APAC",
    "sg": "APAC",
    "new zealand": "APAC",
    "nz": "APAC",
    "china": "APAC",
    "cn": "APAC",
    "asia pacific": "APAC",
    "apac": "APAC",
}

# Industry to category mapping
INDUSTRY_CATEGORIES: dict[str, list[str]] = {
    "restaurant": ["local", "niche"],
    "food": ["local", "niche"],
    "cafe": ["local", "niche"],
    "bar": ["local", "niche"],
    "hotel": ["local", "niche"],
    "hospitality": ["local", "niche"],
    "dentist": ["local", "niche"],
    "dental": ["local", "niche"],
    "doctor": ["local", "niche"],
    "medical": ["local", "niche"],
    "healthcare": ["local", "niche"],
    "lawyer": ["niche", "directory"],
    "attorney": ["niche", "directory"],
    "legal": ["niche", "directory"],
    "plumber": ["local", "niche"],
    "electrician": ["local", "niche"],
    "hvac": ["local", "niche"],
    "contractor": ["local", "niche"],
    "construction": ["local", "niche"],
    "real estate": ["niche", "directory"],
    "realtor": ["niche", "directory"],
    "automotive": ["niche", "local"],
    "car dealer": ["niche", "local"],
    "mechanic": ["local", "niche"],
    "fitness": ["local", "niche"],
    "gym": ["local", "niche"],
    "salon": ["local", "niche"],
    "beauty": ["local", "niche"],
    "spa": ["local", "niche"],
    "retail": ["local", "directory"],
    "ecommerce": ["directory", "niche"],
    "technology": ["directory", "niche"],
    "software": ["directory", "niche"],
    "finance": ["directory", "niche"],
    "accounting": ["niche", "directory"],
    "education": ["education", "directory"],
    "nonprofit": ["directory", "social"],
    "government": ["government"],
}


@dataclass
class ClientProfile:
    """Profile of the client being optimized."""

    name: str
    domain: str
    category: str
    subcategory: str = ""
    country: str = "Australia"
    state: str = ""
    city: str = ""
    postal_code: str = ""
    tier: str = "professional"
    competitor_domains: list[str] = field(default_factory=list)


@dataclass
class SiteScore:
    """Scoring breakdown for a single site."""

    site_id: uuid.UUID
    name: str
    url: str
    category: str | None = None
    importance_score: int = 50
    region: str | None = None
    submission_difficulty: str | None = None

    location_score: int = 0
    authority_score: int = 0
    industry_score: int = 0
    competitor_score: int = 0
    tier_score: int = 0

    total_score: int = 0
    priority: str = "low"
    reasons: list[str] = field(default_factory=list)


class SiteRecommender:
    """Intelligent site recommendation engine."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_recommendations(
        self,
        project: CitationProject,
        client: ClientProfile,
        competitor_site_ids: dict[uuid.UUID, list[str]] | None = None,
        max_recommendations: int = 50,
    ) -> list[SiteScore]:
        """
        Generate ranked list of recommended sites.

        1. Filter by location (keep only sites matching client's country)
        2. Score each site on multiple dimensions
        3. Weight scores by client tier
        4. Rank and deduplicate against existing citations
        5. Return top N with explanation
        """
        client_region = self._resolve_region(client.country)
        weights = TIER_WEIGHTS.get(client.tier, TIER_WEIGHTS["professional"])

        # Get all active sites
        result = await self.session.execute(
            select(CitationSite).where(CitationSite.is_active == True)
        )
        all_sites = result.scalars().all()

        # Get existing submissions for this project (exclude already-submitted)
        existing_result = await self.session.execute(
            select(CitationSubmissionV2.site_id).where(
                CitationSubmissionV2.project_id == project.id,
            )
        )
        existing_site_ids = {row[0] for row in existing_result.all()}

        # Get competitor site IDs if provided
        competitor_sites: dict[uuid.UUID, list[str]] = competitor_site_ids or {}

        scored_sites: list[SiteScore] = []

        for site in all_sites:
            if site.id in existing_site_ids:
                continue

            score = SiteScore(
                site_id=site.id,
                name=site.name,
                url=site.url,
                category=site.category,
                importance_score=getattr(site, "importance_score", 50) or 50,
                region=site.region,
                submission_difficulty=site.submission_difficulty,
            )

            # Score each dimension
            score.location_score = self._score_location(site, client, client_region)
            score.authority_score = self._score_authority(site)
            score.industry_score = self._score_industry(site, client)
            score.competitor_score = self._score_competitors(site, competitor_sites)
            score.tier_score = self._score_tier(site, client.tier)

            # Calculate weighted total
            score.total_score = int(
                score.location_score * weights["location"]
                + score.authority_score * weights["authority"]
                + score.industry_score * weights["industry"]
                + score.competitor_score * weights["competitor"]
                + score.tier_score * 0.0  # tier_score adjusts weights, not a separate dimension
            )

            # Generate reasons
            score.reasons = self._generate_reasons(score, client, client_region, competitor_sites)

            # Map to priority
            score.priority = self._get_priority(score.total_score)

            scored_sites.append(score)

        # Sort by total score descending
        scored_sites.sort(key=lambda s: s.total_score, reverse=True)

        return scored_sites[:max_recommendations]

    def _resolve_region(self, country: str) -> str | None:
        """Resolve a country name/code to a region code."""
        if not country:
            return None
        return COUNTRY_TO_REGION.get(country.lower().strip())

    def _score_location(self, site: CitationSite, client: ClientProfile, client_region: str | None) -> int:
        """Score based on geo_target match (0-100)."""
        site_region = (site.region or "").upper()
        site_geo = (site.geo_target or "").lower()
        client_country = (client.country or "").lower()

        # Exact region match
        if client_region and site_region == client_region.upper():
            return 100

        # Global site — always relevant
        if site_region == "GLOBAL" or site_geo in ("global", "worldwide"):
            return 70

        # Partial country name match
        if client_country and client_country in (site_geo or "").lower():
            return 85

        # Default: low relevance
        return 20

    def _score_authority(self, site: CitationSite) -> int:
        """Score based on domain authority and importance_score."""
        importance = getattr(site, "importance_score", 50) or 50
        da = site.domain_authority or 30

        # Blend importance and DA
        blended = (importance * 0.6) + (da * 0.4)
        return min(int(blended), 100)

    def _score_industry(self, site: CitationSite, client: ClientProfile) -> int:
        """Score based on category match to client's industry."""
        site_cat = (site.category or "").lower()
        client_industry = (client.category or "").lower()

        # Check if client industry maps to this category
        mapped_categories = INDUSTRY_CATEGORIES.get(client_industry, [])

        if site_cat in mapped_categories:
            return 90

        # General/directory sites are always somewhat relevant
        if site_cat in ("general", "directory"):
            return 60

        # Social sites are broadly relevant
        if site_cat == "social":
            return 50

        # Review sites are broadly relevant
        if site_cat == "review":
            return 45

        return 25

    def _score_competitors(self, site: CitationSite, competitor_sites: dict[uuid.UUID, list[str]]) -> int:
        """Score based on competitor presence at this site."""
        if not competitor_sites:
            return 30  # Default when no competitor data

        if site.id in competitor_sites:
            competitor_count = len(competitor_sites[site.id])
            # More competitors here = higher score
            return min(50 + (competitor_count * 15), 100)

        return 10

    def _score_tier(self, site: CitationSite, tier: str) -> int:
        """Score based on client budget tier match."""
        importance = getattr(site, "importance_score", 50) or 50
        is_premium = getattr(site, "is_premium", False) or False
        difficulty = (site.submission_difficulty or "medium").lower()

        if tier == "enterprise":
            # Enterprise: want premium, high-importance sites
            if is_premium and importance >= 80:
                return 100
            if importance >= 60:
                return 70
            return 40

        if tier == "professional":
            # Professional: mix of premium and free
            if importance >= 70:
                return 90
            if importance >= 40:
                return 70
            return 50

        # Starter: free, easy sites
        if is_premium:
            return 20
        if difficulty == "easy":
            return 90
        if difficulty == "medium":
            return 60
        return 30

    def _generate_reasons(
        self,
        score: SiteScore,
        client: ClientProfile,
        client_region: str | None,
        competitor_sites: dict[uuid.UUID, list[str]],
    ) -> list[str]:
        """Generate human-readable reasons for this recommendation."""
        reasons = []

        if score.location_score >= 80:
            reasons.append(f"Matches client location ({client.country})")
        elif score.location_score >= 60:
            reasons.append("Global site, relevant to all regions")

        if score.authority_score >= 80:
            reasons.append(f"High authority (importance: {score.importance_score})")
        elif score.authority_score >= 60:
            reasons.append("Good domain authority")

        if score.industry_score >= 80:
            reasons.append(f"Industry match ({client.category})")
        elif score.industry_score >= 50:
            reasons.append("Relevant category for this business type")

        if score.site_id in competitor_sites:
            comp_names = competitor_sites[score.site_id]
            reasons.append(f"{len(comp_names)} competitor(s) listed here")

        if score.total_score >= 85:
            reasons.append("Critical for local SEO")
        elif score.total_score >= 70:
            reasons.append("High-value citation opportunity")

        return reasons[:3]  # Max 3 reasons

    def _get_priority(self, score: int) -> str:
        """Map score to priority label."""
        if score >= 85:
            return "critical"
        if score >= 70:
            return "high"
        if score >= 50:
            return "medium"
        return "low"
