"""
SEO Platform — Competitor Analyzer Service
===========================================
Scans competitors, builds gap analysis for citation recommendations.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.logging import get_logger
from seo_platform.models.citation_v2 import CitationProject, CitationSite, CitationSubmissionV2
from seo_platform.models.recommendations import CompetitorCitation

logger = get_logger(__name__)


class CompetitorAnalyzer:
    """Analyzes competitor citation profiles to find gaps."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_competitors(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        competitors: list[dict[str, str]],
    ) -> list[CompetitorCitation]:
        """Add competitor domains to a project."""
        saved = []

        for comp in competitors:
            # Check if already exists
            existing = await self.session.execute(
                select(CompetitorCitation).where(
                    CompetitorCitation.project_id == project_id,
                    CompetitorCitation.competitor_domain == comp.get("domain"),
                )
            )
            if existing.scalar_one_or_none():
                continue

            entry = CompetitorCitation(
                project_id=project_id,
                tenant_id=tenant_id,
                competitor_name=comp["name"],
                competitor_domain=comp.get("domain"),
            )
            self.session.add(entry)
            saved.append(entry)

        await self.session.commit()
        return saved

    async def get_competitors(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[CompetitorCitation]:
        """List unique competitors for a project."""
        result = await self.session.execute(
            select(CompetitorCitation).where(
                CompetitorCitation.project_id == project_id,
                CompetitorCitation.tenant_id == tenant_id,
            ).order_by(CompetitorCitation.competitor_name)
        )
        return list(result.scalars().all())

    async def get_competitor_site_map(
        self,
        project_id: uuid.UUID,
    ) -> dict[uuid.UUID, list[str]]:
        """
        Build a map of site_id -> list of competitor names.
        Used by the recommender to score competitor presence.
        """
        result = await self.session.execute(
            select(CompetitorCitation).where(
                CompetitorCitation.project_id == project_id,
                CompetitorCitation.site_id.isnot(None),
            )
        )
        entries = result.scalars().all()

        site_map: dict[uuid.UUID, list[str]] = {}
        for entry in entries:
            if entry.site_id not in site_map:
                site_map[entry.site_id] = []
            if entry.competitor_name not in site_map[entry.site_id]:
                site_map[entry.site_id].append(entry.competitor_name)

        return site_map

    async def build_gap_analysis(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """
        Compare client citations vs competitor citations.
        Return sites where competitors appear but client doesn't.
        """
        # Get client's existing submission site IDs
        existing_result = await self.session.execute(
            select(CitationSubmissionV2.site_id).where(
                CitationSubmissionV2.project_id == project_id,
            )
        )
        client_site_ids = {row[0] for row in existing_result.all()}

        # Get competitor citations with site info
        comp_result = await self.session.execute(
            select(
                CompetitorCitation.site_id,
                CompetitorCitation.competitor_name,
                CitationSite.name,
                CitationSite.url,
                CitationSite.importance_score,
            ).join(
                CitationSite,
                CompetitorCitation.site_id == CitationSite.id,
                isouter=True,
            ).where(
                CompetitorCitation.project_id == project_id,
                CompetitorCitation.site_id.isnot(None),
            )
        )
        rows = comp_result.all()

        # Build gap analysis: sites where competitors are but client isn't
        site_gaps: dict[uuid.UUID, dict] = {}
        for site_id, comp_name, site_name, site_url, importance in rows:
            if not site_id:
                continue

            if site_id not in site_gaps:
                site_gaps[site_id] = {
                    "site_id": site_id,
                    "site_name": site_name or "Unknown",
                    "site_url": site_url or "",
                    "site_importance": importance or 50,
                    "competitor_count": 0,
                    "competitor_names": [],
                    "is_client_listed": site_id in client_site_ids,
                }

            gap = site_gaps[site_id]
            if comp_name not in gap["competitor_names"]:
                gap["competitor_names"].append(comp_name)
                gap["competitor_count"] = len(gap["competitor_names"])

        # Sort by competitor count descending, filter to gaps only
        gaps = [
            g for g in site_gaps.values()
            if not g["is_client_listed"] and g["competitor_count"] > 0
        ]
        gaps.sort(key=lambda g: (-g["competitor_count"], -g["site_importance"]))

        return gaps

    async def save_competitor_citations(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        competitor_data: list[dict[str, Any]],
    ) -> int:
        """Persist competitor citation data from research/scraping."""
        saved = 0

        for entry in competitor_data:
            comp_citation = CompetitorCitation(
                project_id=project_id,
                tenant_id=tenant_id,
                competitor_name=entry.get("competitor_name", "Unknown"),
                competitor_domain=entry.get("competitor_domain"),
                site_id=entry.get("site_id"),
                site_url=entry.get("site_url"),
                citation_url=entry.get("citation_url"),
                has_images=entry.get("has_images", False),
                has_complete_nap=entry.get("has_complete_nap", False),
                citation_age_months=entry.get("citation_age_months"),
                domain_rating=entry.get("domain_rating"),
            )
            self.session.add(comp_citation)
            saved += 1

        await self.session.commit()
        return saved

    async def get_competitor_stats(
        self,
        project_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get statistics about competitor data for a project."""
        # Count unique competitors
        comp_result = await self.session.execute(
            select(func.count(func.distinct(CompetitorCitation.competitor_name))).where(
                CompetitorCitation.project_id == project_id,
            )
        )
        unique_competitors = comp_result.scalar() or 0

        # Count total competitor citations
        total_result = await self.session.execute(
            select(func.count()).where(
                CompetitorCitation.project_id == project_id,
            )
        )
        total_citations = total_result.scalar() or 0

        # Count unique competitor sites
        sites_result = await self.session.execute(
            select(func.count(func.distinct(CompetitorCitation.site_id))).where(
                CompetitorCitation.project_id == project_id,
                CompetitorCitation.site_id.isnot(None),
            )
        )
        unique_sites = sites_result.scalar() or 0

        return {
            "unique_competitors": unique_competitors,
            "total_citations": total_citations,
            "unique_sites": unique_sites,
        }
