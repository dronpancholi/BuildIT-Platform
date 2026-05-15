"""
SEO Platform — Local SEO & Citation Intelligence Service
==========================================================
Directory quality scoring, local authority analysis, NAP consistency,
geo SEO mapping, citation opportunity scoring, and local competitor intelligence.

Architecture axiom: AI proposes. Deterministic systems execute.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------
class DirectoryQualityScore(BaseModel):
    directory_name: str
    composite_score: float = 0.0
    domain_authority: float = 0.0
    category_relevance: float = 0.0
    geographic_relevance: float = 0.0
    citation_consistency: float = 0.0
    spam_score: float = 0.0
    breakdown: dict[str, Any] = Field(default_factory=dict)


class CitationEntry(BaseModel):
    directory: str
    nap_consistent: bool = False
    authority_score: float = 0.0
    url: str = ""


class CompetitorCitationComparison(BaseModel):
    competitor_domain: str
    citation_count: int = 0
    avg_authority: float = 0.0
    directories_listed: list[str] = Field(default_factory=list)


class LocalAuthorityReport(BaseModel):
    business_name: str
    authority_score: float = 0.0
    consistent_citation_count: int = 0
    directory_diversity: int = 0
    geographic_coverage: dict[str, int] = Field(default_factory=dict)
    avg_citation_authority: float = 0.0
    review_presence: dict[str, Any] = Field(default_factory=dict)
    competitor_comparison: list[CompetitorCitationComparison] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)


class NAPVariation(BaseModel):
    field: str
    original: str = ""
    variation: str = ""
    type: str = ""


class NAPConsistencyReport(BaseModel):
    business_name: str
    consistency_score: float = 0.0
    exact_match_count: int = 0
    total_citations_checked: int = 0
    variations_found: list[NAPVariation] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class GeoLocationInfo(BaseModel):
    city: str = ""
    state: str = ""
    competitor_density: int = 0
    estimated_search_volume: int = 0
    citation_gaps: list[str] = Field(default_factory=list)
    opportunity_score: float = 0.0


class GeoSEOMap(BaseModel):
    business_name: str
    radius_miles: int = 25
    locations: list[GeoLocationInfo] = Field(default_factory=list)
    top_opportunities: list[str] = Field(default_factory=list)


class CitationOpportunity(BaseModel):
    directory: str
    opportunity_score: float = 0.0
    directory_authority: float = 0.0
    relevance_score: float = 0.0
    geographic_match: float = 0.0
    gap: bool = True
    competition_presence: int = 0
    effort_estimate: str = ""
    impact_estimate: str = ""


class CompetitorCitationProfile(BaseModel):
    domain: str
    citation_count: int = 0
    directory_distribution: dict[str, int] = Field(default_factory=dict)
    avg_authority: float = 0.0


class LocalCompetitorIntelligence(BaseModel):
    business_name: str
    competitors: list[CompetitorCitationProfile] = Field(default_factory=list)
    citation_gaps_vs_competitors: list[dict[str, Any]] = Field(default_factory=list)
    priority_targets: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Deterministic directory authority tiers
# ---------------------------------------------------------------------------
_DIRECTORY_AUTHORITY: dict[str, float] = {
    "google_business_profile": 95.0,
    "yelp": 90.0,
    "facebook_business": 85.0,
    "apple_maps": 80.0,
    "bing_places": 75.0,
    "yellowpages": 70.0,
    "superpages": 65.0,
    "foursquare": 70.0,
    "tripadvisor": 85.0,
    "bbb": 80.0,
    "merchant_circle": 65.0,
    "mapquest": 60.0,
    "citysearch": 55.0,
    "hotfrog": 45.0,
    "manta": 50.0,
    "ezlocal": 40.0,
    "chamber_of_commerce": 70.0,
    "angies_list": 75.0,
    "nextdoor": 65.0,
    "whitepages": 60.0,
    "cylex": 40.0,
    "kompass": 50.0,
    "brownbook": 35.0,
    "tupalo": 30.0,
    "opendi": 25.0,
}

_DIRECTORY_CATEGORIES: dict[str, list[str]] = {
    "general": ["yellowpages", "superpages", "citysearch", "hotfrog", "manta", "whitepages", "cylex", "kompass", "brownbook", "tupalo", "opendi"],
    "social": ["facebook_business", "foursquare", "nextdoor"],
    "review": ["yelp", "tripadvisor", "angies_list", "bbb"],
    "maps": ["google_business_profile", "apple_maps", "bing_places", "mapquest"],
    "local": ["ezlocal", "chamber_of_commerce", "merchant_circle"],
}

_GEO_TIERS: dict[str, float] = {
    "local": 1.0,
    "regional": 0.7,
    "national": 0.4,
    "global": 0.2,
}

_DIRECTORY_GEO: dict[str, str] = {
    "google_business_profile": "local",
    "yelp": "local",
    "facebook_business": "global",
    "apple_maps": "local",
    "bing_places": "local",
    "yellowpages": "national",
    "superpages": "national",
    "foursquare": "global",
    "tripadvisor": "global",
    "bbb": "regional",
    "merchant_circle": "national",
    "mapquest": "national",
    "citysearch": "national",
    "hotfrog": "global",
    "manta": "national",
    "ezlocal": "local",
    "chamber_of_commerce": "local",
    "angies_list": "national",
    "nextdoor": "local",
    "whitepages": "national",
    "cylex": "global",
    "kompass": "global",
    "brownbook": "global",
    "tupalo": "global",
    "opendi": "global",
}

_SPAM_DIRECTORY_SIGNALS: dict[str, float] = {
    "opendi": 0.4,
    "tupalo": 0.3,
    "brownbook": 0.3,
    "cylex": 0.2,
    "hotfrog": 0.2,
}


# ---------------------------------------------------------------------------
# Local SEO Intelligence Service
# ---------------------------------------------------------------------------
class LocalSEOIntelligenceService:

    def score_directory_quality(
        self,
        directory_name: str,
        directory_data: dict[str, Any] | None = None,
    ) -> DirectoryQualityScore:
        """Score a citation directory across quality dimensions (0-100)."""
        normalized_name = directory_name.lower().replace(" ", "_").replace("-", "_")

        da = _DIRECTORY_AUTHORITY.get(normalized_name, 30.0)

        business_category = (directory_data or {}).get("business_category", "").lower()
        directory_category = None
        for cat, members in _DIRECTORY_CATEGORIES.items():
            if normalized_name in members:
                directory_category = cat
                break

        if directory_category and business_category:
            relevant_categories = {
                "general": ["general", "business", "services"],
                "social": ["social", "media", "community"],
                "review": ["review", "hospitality", "restaurant", "services"],
                "maps": ["maps", "navigation", "local", "travel"],
                "local": ["local", "community", "business", "services"],
            }
            matched = relevant_categories.get(directory_category, ["general"])
            category_relevance = 0.8 if business_category in matched else 0.5
        else:
            category_relevance = 0.5

        geo_tier = _DIRECTORY_GEO.get(normalized_name, "national")
        geo_relevance = _GEO_TIERS.get(geo_tier, 0.4)

        consistency_score = 0.7
        if da >= 70:
            consistency_score += 0.15
        if normalized_name not in _SPAM_DIRECTORY_SIGNALS:
            consistency_score += 0.1
        consistency_score = min(1.0, consistency_score)

        spam = _SPAM_DIRECTORY_SIGNALS.get(normalized_name, 0.0)

        composite = (
            (da / 100.0) * 0.30
            + category_relevance * 0.25
            + geo_relevance * 0.15
            + consistency_score * 0.20
            - spam * 0.10
        )
        composite = max(0.0, min(1.0, composite)) * 100

        return DirectoryQualityScore(
            directory_name=directory_name,
            composite_score=round(composite, 1),
            domain_authority=da,
            category_relevance=round(category_relevance, 4),
            geographic_relevance=round(geo_relevance, 4),
            citation_consistency=round(consistency_score, 4),
            spam_score=round(spam, 4),
            breakdown={
                "geo_tier": geo_tier,
                "directory_category": directory_category or "unknown",
                "authority_tier": "high" if da >= 70 else "medium" if da >= 40 else "low",
            },
        )

    async def analyze_local_authority(
        self,
        business_profile: dict[str, Any],
        existing_citations: list[dict[str, Any]] | None = None,
        competitor_citations: list[dict[str, Any]] | None = None,
    ) -> LocalAuthorityReport:
        """Assess local SEO authority from real citation data."""
        business_name = business_profile.get("business_name", "Unknown")
        logger.info("analyzing_local_authority", business=business_name)

        citations = existing_citations or []

        consistent_count = sum(
            1 for c in citations if c.get("nap_consistent", False)
        )
        total_count = len(citations) if citations else 1

        directories_used = set()
        geo_coverage: dict[str, int] = {}
        total_authority = 0.0

        for c in citations:
            dir_name = c.get("directory", "").lower().replace(" ", "_").replace("-", "_")
            directories_used.add(dir_name)
            da = _DIRECTORY_AUTHORITY.get(dir_name, 30.0)
            total_authority += da

            geo_tier = _DIRECTORY_GEO.get(dir_name, "national")
            geo_coverage[geo_tier] = geo_coverage.get(geo_tier, 0) + 1

        directory_diversity = len(directories_used)
        avg_authority = total_authority / max(len(citations), 1)

        review_data = business_profile.get("reviews", {})
        review_presence = {
            "total_reviews": review_data.get("total_reviews", 0),
            "average_rating": review_data.get("average_rating", 0.0),
            "platform_diversity": len(review_data.get("platforms", [])),
        }

        competitor_comparison_list: list[CompetitorCitationComparison] = []
        if competitor_citations:
            for comp in competitor_citations:
                comp_dirs = comp.get("directories", [])
                comp_total_authority = 0.0
                for d in comp_dirs:
                    dn = d.lower().replace(" ", "_").replace("-", "_")
                    comp_total_authority += _DIRECTORY_AUTHORITY.get(dn, 30.0)
                competitor_comparison_list.append(CompetitorCitationComparison(
                    competitor_domain=comp.get("domain", ""),
                    citation_count=len(comp_dirs),
                    avg_authority=round(comp_total_authority / max(len(comp_dirs), 1), 1),
                    directories_listed=comp_dirs,
                ))

        authority_score = (
            (consistent_count / max(total_count, 1)) * 0.30
            + min(1.0, directory_diversity / 10) * 0.20
            + min(1.0, avg_authority / 100) * 0.20
            + min(1.0, (review_presence["total_reviews"] or 0) / 50) * 0.15
            + min(1.0, len(geo_coverage) / 3) * 0.15
        ) * 100

        gaps: list[str] = []
        opportunities: list[str] = []

        for dir_name in ["google_business_profile", "yelp", "facebook_business", "apple_maps", "bbb", "tripadvisor"]:
            if dir_name not in directories_used:
                gaps.append(f"Not listed on {dir_name.replace('_', ' ').title()}")
                if _DIRECTORY_AUTHORITY.get(dir_name, 0) >= 70:
                    opportunities.append(f"High-priority: claim {dir_name.replace('_', ' ').title()} listing")

        if review_presence["platform_diversity"] < 2:
            opportunities.append("Expand review platform presence beyond current platforms")
        if directory_diversity < 5:
            opportunities.append(f"Target {5 - directory_diversity} more citation directories")

        return LocalAuthorityReport(
            business_name=business_name,
            authority_score=round(authority_score, 1),
            consistent_citation_count=consistent_count,
            directory_diversity=directory_diversity,
            geographic_coverage=geo_coverage,
            avg_citation_authority=round(avg_authority, 1),
            review_presence=review_presence,
            competitor_comparison=competitor_comparison_list,
            gaps=gaps,
            opportunities=opportunities,
        )

    def analyze_nap_consistency(
        self,
        business_name: str,
        phone: str,
        address: dict[str, str],
        existing_citations: list[dict[str, Any]] | None = None,
    ) -> NAPConsistencyReport:
        """Detect NAP inconsistencies across existing citations."""
        logger.info("analyzing_nap_consistency", business=business_name)

        citations = existing_citations or []

        variations: list[NAPVariation] = []
        exact_matches = 0

        canonical_name = business_name.strip().lower()
        canonical_phone = re.sub(r"[^\d]", "", phone)
        canonical_street = address.get("street", "").strip().lower()
        canonical_city = address.get("city", "").strip().lower()
        canonical_state = address.get("state", "").strip().upper()
        canonical_zip = address.get("zip", "").strip()

        abbreviation_map = {
            "street": "st", "st": "street",
            "avenue": "ave", "ave": "avenue",
            "road": "rd", "rd": "road",
            "drive": "dr", "dr": "drive",
            "lane": "ln", "ln": "lane",
            "boulevard": "blvd", "blvd": "boulevard",
            "court": "ct", "ct": "court",
            "place": "pl", "pl": "place",
            "company": "co", "co": "company",
            "corporation": "corp", "corp": "corporation",
            "incorporated": "inc", "inc": "incorporated",
            "limited": "ltd", "ltd": "limited",
            "suite": "ste", "ste": "suite",
            "apartment": "apt", "apt": "apartment",
        }

        for citation in citations:
            is_match = True

            citation_name = citation.get("business_name", "").strip().lower()
            citation_phone = re.sub(r"[^\d]", "", citation.get("phone", ""))
            citation_street = citation.get("street", "").strip().lower()
            citation_city = citation.get("city", "").strip().lower()
            citation_state = citation.get("state", "").strip().upper()
            citation_zip = citation.get("zip", "").strip()

            if citation_name and citation_name != canonical_name:
                name_variation = citation_name
                a, b = canonical_name, citation_name
                for abbr_from, abbr_to in abbreviation_map.items():
                    a = a.replace(abbr_from, abbr_to)
                    b = b.replace(abbr_from, abbr_to)
                if a != b:
                    variations.append(NAPVariation(
                        field="business_name",
                        original=business_name,
                        variation=citation.get("business_name", ""),
                        type="abbreviation_mismatch" if any(
                            w in citation_name for w in ["st", "ave", "co", "inc", "ltd", "corp"]
                        ) else "name_mismatch",
                    ))
                    is_match = False

            if citation_phone and citation_phone != canonical_phone:
                variations.append(NAPVariation(
                    field="phone",
                    original=phone,
                    variation=citation.get("phone", ""),
                    type="phone_format_mismatch",
                ))
                is_match = False

            if citation_street and citation_street != canonical_street:
                a, b = canonical_street, citation_street
                for abbr_from, abbr_to in abbreviation_map.items():
                    a = a.replace(abbr_from, abbr_to)
                    b = b.replace(abbr_from, abbr_to)
                if a != b:
                    variations.append(NAPVariation(
                        field="address",
                        original=address.get("street", ""),
                        variation=citation.get("street", ""),
                        type="address_mismatch",
                    ))
                    is_match = False

            if citation_city and citation_city != canonical_city:
                variations.append(NAPVariation(
                    field="city",
                    original=canonical_city,
                    variation=citation.get("city", ""),
                    type="city_mismatch",
                ))
                is_match = False

            if citation_state and citation_state != canonical_state:
                variations.append(NAPVariation(
                    field="state",
                    original=canonical_state,
                    variation=citation.get("state", ""),
                    type="state_mismatch",
                ))
                is_match = False

            if citation_zip and citation_zip != canonical_zip:
                variations.append(NAPVariation(
                    field="zip",
                    original=canonical_zip,
                    variation=citation.get("zip", ""),
                    type="zip_mismatch",
                ))
                is_match = False

            if is_match:
                exact_matches += 1

        total_checked = len(citations) or 1
        base_score = exact_matches / max(total_checked, 1)
        variation_penalty = len(variations) * 0.05
        consistency_score = max(0.0, base_score - variation_penalty) * 100

        recommendations: list[str] = []
        if variations:
            for v in variations:
                recommendations.append(
                    f"Fix {v.field}: change '{v.variation}' to match canonical '{v.original}'"
                )
        missing_fields = []
        for c in citations:
            for field in ["business_name", "phone", "street", "city", "state", "zip"]:
                if not c.get(field):
                    missing_fields.append(field)
        if missing_fields:
            unique_missing = list(set(missing_fields))
            recommendations.append(f"Add missing NAP fields: {', '.join(unique_missing)}")
        if not recommendations:
            recommendations.append("NAP is consistent across all citations")

        return NAPConsistencyReport(
            business_name=business_name,
            consistency_score=round(consistency_score, 1),
            exact_match_count=exact_matches,
            total_citations_checked=len(citations),
            variations_found=variations,
            recommendations=recommendations,
        )

    def build_geo_seo_map(
        self,
        business_profile: dict[str, Any],
        radius_miles: int = 25,
        location_data: list[dict[str, Any]] | None = None,
    ) -> GeoSEOMap:
        """Build geographic SEO map with scores and opportunities per location."""
        business_name = business_profile.get("business_name", "Unknown")
        logger.info("building_geo_seo_map", business=business_name, radius=radius_miles)

        locations: list[GeoLocationInfo] = []
        city = business_profile.get("city", "")
        state = business_profile.get("state_province", "")

        if location_data:
            for loc in location_data:
                competitor_density = loc.get("competitor_density", 0)
                search_volume = loc.get("estimated_search_volume", 0)
                citation_gaps = loc.get("citation_gaps", [])

                opportunity = (
                    min(1.0, search_volume / 1000) * 0.40
                    + min(1.0, 1.0 / max(competitor_density, 1)) * 0.30
                    + min(1.0, len(citation_gaps) / 5) * 0.30
                ) * 100

                locations.append(GeoLocationInfo(
                    city=loc.get("city", ""),
                    state=loc.get("state", ""),
                    competitor_density=competitor_density,
                    estimated_search_volume=search_volume,
                    citation_gaps=citation_gaps,
                    opportunity_score=round(opportunity, 1),
                ))

        if not locations and city:
            locations.append(GeoLocationInfo(
                city=city,
                state=state,
                competitor_density=0,
                estimated_search_volume=0,
                citation_gaps=[],
                opportunity_score=50.0,
            ))

        locations.sort(key=lambda x: x.opportunity_score, reverse=True)
        top_opportunities = [
            f"{l.city}, {l.state}" for l in locations[:3] if l.opportunity_score >= 50
        ]

        return GeoSEOMap(
            business_name=business_name,
            radius_miles=radius_miles,
            locations=locations,
            top_opportunities=top_opportunities,
        )

    def score_citation_opportunity(
        self,
        business_profile: dict[str, Any],
        directories: list[dict[str, Any]] | None = None,
    ) -> list[CitationOpportunity]:
        """Score which citation directories to target."""
        business_name = business_profile.get("business_name", "Unknown")
        logger.info("scoring_citation_opportunities", business=business_name)

        existing_dirs = set()
        if directories:
            for d in directories:
                if d.get("listed", False):
                    dn = d.get("name", "").lower().replace(" ", "_").replace("-", "_")
                    existing_dirs.add(dn)

        opportunities: list[CitationOpportunity] = []

        for dir_name, da in sorted(_DIRECTORY_AUTHORITY.items(), key=lambda x: x[1], reverse=True):
            normalized = dir_name.lower().replace(" ", "_").replace("-", "_")
            is_listed = normalized in existing_dirs

            geo_tier = _DIRECTORY_GEO.get(normalized, "national")
            geo_match = _GEO_TIERS.get(geo_tier, 0.4)

            competition_presence = 3
            for d in (directories or []):
                if d.get("name", "").lower().replace(" ", "_").replace("-", "_") == normalized:
                    competition_presence = d.get("competitor_count", 0)
                    break

            if is_listed:
                gap_score = 0.1
            else:
                gap_score = 1.0

            opportunity = (
                (da / 100.0) * 0.30
                + 0.5 * 0.20
                + geo_match * 0.15
                + gap_score * 0.25
                + min(1.0, competition_presence / 10) * 0.10
            ) * 100

            if is_listed:
                continue

            effort = "low" if da >= 70 else "medium" if da >= 40 else "high"
            impact = "high" if da >= 70 else "medium" if da >= 40 else "low"

            opportunities.append(CitationOpportunity(
                directory=dir_name.replace("_", " ").title(),
                opportunity_score=round(opportunity, 1),
                directory_authority=da,
                relevance_score=0.5,
                geographic_match=round(geo_match, 2),
                gap=not is_listed,
                competition_presence=competition_presence,
                effort_estimate=effort,
                impact_estimate=impact,
            ))

        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        return opportunities[:20]

    def analyze_local_competitors(
        self,
        business_profile: dict[str, Any],
        competitors: list[dict[str, Any]] | None = None,
    ) -> LocalCompetitorIntelligence:
        """Analyze local competitor citation landscape."""
        business_name = business_profile.get("business_name", "Unknown")
        logger.info("analyzing_local_competitors", business=business_name)

        competitor_profiles: list[CompetitorCitationProfile] = []

        all_competitor_dirs: set[str] = set()
        our_dirs: set[str] = set()

        for c in (competitors or []):
            dirs = c.get("directories", [])
            total_authority = 0.0
            dist: dict[str, int] = {}
            for d in dirs:
                dn = d.lower().replace(" ", "_").replace("-", "_")
                all_competitor_dirs.add(dn)
                dist[dn] = dist.get(dn, 0) + 1
                total_authority += _DIRECTORY_AUTHORITY.get(dn, 30.0)
            competitor_profiles.append(CompetitorCitationProfile(
                domain=c.get("domain", ""),
                citation_count=len(dirs),
                directory_distribution=dist,
                avg_authority=round(total_authority / max(len(dirs), 1), 1),
            ))

        business_dirs = business_profile.get("directories", [])
        for d in business_dirs:
            dn = d.lower().replace(" ", "_").replace("-", "_")
            our_dirs.add(dn)

        citation_gaps: list[dict[str, Any]] = []
        for dir_name in all_competitor_dirs:
            normalized = dir_name.lower().replace(" ", "_").replace("-", "_")
            if normalized not in our_dirs:
                competitor_count = sum(
                    1 for cp in competitor_profiles if normalized in cp.directory_distribution
                )
                citation_gaps.append({
                    "directory": dir_name.replace("_", " ").title(),
                    "competitors_listed": competitor_count,
                    "authority": _DIRECTORY_AUTHORITY.get(normalized, 30.0),
                    "priority": "high" if _DIRECTORY_AUTHORITY.get(normalized, 0) >= 70 else "medium",
                })

        citation_gaps.sort(key=lambda x: (-x["authority"], -x["competitors_listed"]))

        priority_targets = [
            g["directory"] for g in citation_gaps[:5]
        ]

        competitor_profiles.sort(key=lambda x: x.citation_count, reverse=True)

        return LocalCompetitorIntelligence(
            business_name=business_name,
            competitors=competitor_profiles,
            citation_gaps_vs_competitors=citation_gaps,
            priority_targets=priority_targets,
        )


local_seo_intelligence = LocalSEOIntelligenceService()
