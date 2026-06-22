"""
SEO Platform — Recommendations API
====================================
Endpoints for smart site recommendations and competitor analysis.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.models.citation_v2 import CitationProject, CitationSite
from seo_platform.models.recommendations import CitationRecommendation, CompetitorCitation
from seo_platform.schemas import APIResponse
from seo_platform.schemas.recommendation import (
    BulkAcceptRequest,
    CompetitorBulkCreate,
    CompetitorResponse,
    GapAnalysisResponse,
    GenerateRecommendationsRequest,
    RecommendationResponse,
    RecommendationStats,
    RecommendationSummary,
    UpdateRecommendationRequest,
)
from seo_platform.services.competitor_analyzer import CompetitorAnalyzer
from seo_platform.services.site_recommender import ClientProfile, SiteRecommender

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /citations/projects/{id}/recommendations — Generate recommendations
# ---------------------------------------------------------------------------
@router.post(
    "/projects/{project_id}/recommendations",
    response_model=APIResponse[dict[str, Any]],
)
async def generate_recommendations(
    project_id: uuid.UUID,
    request: GenerateRecommendationsRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict[str, Any]]:
    """Generate smart site recommendations for a project."""
    async with get_session() as session:
        # Get project
        result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Build client profile
        client = ClientProfile(
            name=project.business_name,
            domain=project.website_url or "",
            category=project.category or "general",
            country=project.country or "Australia",
            state=project.state or "",
            city=project.city or "",
            tier="professional",  # Default tier
            competitor_domains=request.competitor_domains,
        )

        # Build competitor site map
        comp_analyzer = CompetitorAnalyzer(session)
        competitor_site_map = await comp_analyzer.get_competitor_site_map(project_id)

        # Generate recommendations
        recommender = SiteRecommender(session)
        scores = await recommender.generate_recommendations(
            project=project,
            client=client,
            competitor_site_ids=competitor_site_map,
            max_recommendations=request.max_results,
        )

        # Save recommendations to DB
        saved_count = 0
        for score in scores:
            # Check if already exists
            existing = await session.execute(
                select(CitationRecommendation).where(
                    CitationRecommendation.project_id == project_id,
                    CitationRecommendation.site_id == score.site_id,
                )
            )
            if existing.scalar_one_or_none() and not request.force_regenerate:
                continue

            rec = CitationRecommendation(
                project_id=project_id,
                tenant_id=tenant_id,
                site_id=score.site_id,
                priority_score=score.total_score,
                priority_reason=score.reasons[0] if score.reasons else None,
                recommendation_type=_map_type(score),
                scoring_breakdown={
                    "location_score": score.location_score,
                    "authority_score": score.authority_score,
                    "industry_score": score.industry_score,
                    "competitor_score": score.competitor_score,
                    "tier_score": score.tier_score,
                },
            )
            session.add(rec)
            saved_count += 1

        await session.commit()

        # Build response
        summary = RecommendationSummary(
            total=len(scores),
            pending=saved_count,
            critical=sum(1 for s in scores if s.priority == "critical"),
            high=sum(1 for s in scores if s.priority == "high"),
            medium=sum(1 for s in scores if s.priority == "medium"),
            low=sum(1 for s in scores if s.priority == "low"),
        )

        recommendations_data = []
        for score in scores[:50]:
            recommendations_data.append({
                "site_id": str(score.site_id),
                "site_name": score.name,
                "site_url": score.url,
                "site_category": score.category,
                "site_importance": score.importance_score,
                "site_region": score.region,
                "priority_score": score.total_score,
                "priority": score.priority,
                "reasons": score.reasons,
                "scoring_breakdown": {
                    "location_score": score.location_score,
                    "authority_score": score.authority_score,
                    "industry_score": score.industry_score,
                    "competitor_score": score.competitor_score,
                    "tier_score": score.tier_score,
                },
            })

        return APIResponse(
            data={
                "recommendations": recommendations_data,
                "summary": summary.model_dump(),
                "saved_count": saved_count,
            }
        )


def _map_type(score) -> str:
    """Map a SiteScore to a recommendation type string."""
    if score.competitor_score >= 70:
        return "competitor_gap"
    if score.location_score >= 80:
        return "location_match"
    if score.industry_score >= 80:
        return "industry_match"
    if score.authority_score >= 80:
        return "high_authority"
    return "tier_match"


# ---------------------------------------------------------------------------
# GET /citations/projects/{id}/recommendations — List saved recommendations
# ---------------------------------------------------------------------------
@router.get(
    "/projects/{project_id}/recommendations",
    response_model=APIResponse[list[RecommendationResponse]],
)
async def list_recommendations(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> APIResponse[list[RecommendationResponse]]:
    """List saved recommendations for a project."""
    async with get_session() as session:
        query = (
            select(CitationRecommendation, CitationSite)
            .join(CitationSite, CitationRecommendation.site_id == CitationSite.id, isouter=True)
            .where(
                CitationRecommendation.project_id == project_id,
                CitationRecommendation.tenant_id == tenant_id,
            )
        )

        if status:
            query = query.where(CitationRecommendation.status == status)

        # Count
        count_result = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        offset = (page - 1) * per_page
        query = query.order_by(CitationRecommendation.priority_score.desc())
        query = query.offset(offset).limit(per_page)

        result = await session.execute(query)
        rows = result.all()

        recommendations = []
        for rec, site in rows:
            recommendations.append(
                RecommendationResponse(
                    id=rec.id,
                    project_id=rec.project_id,
                    site_id=rec.site_id,
                    site_name=site.name if site else None,
                    site_url=site.url if site else None,
                    site_category=site.category if site else None,
                    site_importance=getattr(site, "importance_score", None) if site else None,
                    site_region=site.region if site else None,
                    site_difficulty=site.submission_difficulty if site else None,
                    priority_score=rec.priority_score,
                    priority_reason=rec.priority_reason,
                    recommendation_type=rec.recommendation_type,
                    status=rec.status,
                    scoring_breakdown=rec.scoring_breakdown,
                    created_at=rec.created_at,
                    updated_at=rec.updated_at,
                )
            )

        return APIResponse(
            data=recommendations,
            meta={"total": total, "offset": offset, "limit": per_page},
        )


# ---------------------------------------------------------------------------
# PUT /citations/recommendations/{id} — Update status
# ---------------------------------------------------------------------------
@router.put(
    "/recommendations/{recommendation_id}",
    response_model=APIResponse[RecommendationResponse],
)
async def update_recommendation(
    recommendation_id: uuid.UUID,
    request: UpdateRecommendationRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[RecommendationResponse]:
    """Update recommendation status (accept/reject)."""
    async with get_session() as session:
        result = await session.execute(
            select(CitationRecommendation).where(
                CitationRecommendation.id == recommendation_id,
                CitationRecommendation.tenant_id == tenant_id,
            )
        )
        rec = result.scalar_one_or_none()
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        rec.status = request.status
        if request.notes:
            rec.notes = request.notes

        await session.commit()
        await session.refresh(rec)

        # Get site info
        site_result = await session.execute(
            select(CitationSite).where(CitationSite.id == rec.site_id)
        )
        site = site_result.scalar_one_or_none()

        return APIResponse(
            data=RecommendationResponse(
                id=rec.id,
                project_id=rec.project_id,
                site_id=rec.site_id,
                site_name=site.name if site else None,
                site_url=site.url if site else None,
                site_category=site.category if site else None,
                site_importance=getattr(site, "importance_score", None) if site else None,
                site_region=site.region if site else None,
                site_difficulty=site.submission_difficulty if site else None,
                priority_score=rec.priority_score,
                priority_reason=rec.priority_reason,
                recommendation_type=rec.recommendation_type,
                status=rec.status,
                scoring_breakdown=rec.scoring_breakdown,
                created_at=rec.created_at,
                updated_at=rec.updated_at,
            )
        )


# ---------------------------------------------------------------------------
# POST /citations/recommendations/bulk-accept — Accept multiple
# ---------------------------------------------------------------------------
@router.post(
    "/recommendations/bulk-accept",
    response_model=APIResponse[dict[str, int]],
)
async def bulk_accept_recommendations(
    request: BulkAcceptRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict[str, int]]:
    """Accept multiple recommendations at once."""
    async with get_session() as session:
        result = await session.execute(
            select(CitationRecommendation).where(
                CitationRecommendation.id.in_(request.recommendation_ids),
                CitationRecommendation.tenant_id == tenant_id,
            )
        )
        recs = result.scalars().all()

        updated = 0
        for rec in recs:
            rec.status = "accepted"
            updated += 1

        await session.commit()

        return APIResponse(data={"updated": updated})


# ---------------------------------------------------------------------------
# POST /citations/projects/{id}/competitors — Add competitors
# ---------------------------------------------------------------------------
@router.post(
    "/projects/{project_id}/competitors",
    response_model=APIResponse[dict[str, int]],
)
async def add_competitors(
    project_id: uuid.UUID,
    request: CompetitorBulkCreate,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict[str, int]]:
    """Add competitor domains to a project."""
    async with get_session() as session:
        # Verify project exists
        proj_result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        if not proj_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")

        analyzer = CompetitorAnalyzer(session)
        competitors = [c.model_dump() for c in request.competitors]
        saved = await analyzer.add_competitors(project_id, tenant_id, competitors)

        return APIResponse(data={"added": len(saved)})


# ---------------------------------------------------------------------------
# GET /citations/projects/{id}/competitors — List competitors + gaps
# ---------------------------------------------------------------------------
@router.get(
    "/projects/{project_id}/competitors",
    response_model=APIResponse[dict[str, Any]],
)
async def list_competitors(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict[str, Any]]:
    """List competitors and their citation gap analysis."""
    async with get_session() as session:
        # Verify project
        proj_result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        if not proj_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")

        analyzer = CompetitorAnalyzer(session)

        # Get competitors
        competitors = await analyzer.get_competitors(project_id, tenant_id)
        comp_list = [
            CompetitorResponse(
                id=c.id,
                project_id=c.project_id,
                competitor_name=c.competitor_name,
                competitor_domain=c.competitor_domain,
                site_id=c.site_id,
                site_url=c.site_url,
                citation_url=c.citation_url,
                has_images=c.has_images,
                has_complete_nap=c.has_complete_nap,
                citation_age_months=c.citation_age_months,
                domain_rating=c.domain_rating,
                created_at=c.created_at,
            )
            for c in competitors
        ]

        # Get gap analysis
        gaps = await analyzer.build_gap_analysis(project_id, tenant_id)

        # Get stats
        stats = await analyzer.get_competitor_stats(project_id)

        return APIResponse(
            data={
                "competitors": comp_list,
                "gaps": gaps[:50],
                "stats": stats,
            }
        )


# ---------------------------------------------------------------------------
# GET /citations/projects/{id}/recommendations/stats — Summary stats
# ---------------------------------------------------------------------------
@router.get(
    "/projects/{project_id}/recommendations/stats",
    response_model=APIResponse[RecommendationStats],
)
async def get_recommendation_stats(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[RecommendationStats]:
    """Get recommendation stats for a project."""
    async with get_session() as session:
        # Total recommendations
        total_result = await session.execute(
            select(func.count()).where(
                CitationRecommendation.project_id == project_id,
                CitationRecommendation.tenant_id == tenant_id,
            )
        )
        total = total_result.scalar() or 0

        # Accepted
        accepted_result = await session.execute(
            select(func.count()).where(
                CitationRecommendation.project_id == project_id,
                CitationRecommendation.tenant_id == tenant_id,
                CitationRecommendation.status == "accepted",
            )
        )
        accepted = accepted_result.scalar() or 0

        # Average priority
        avg_result = await session.execute(
            select(func.avg(CitationRecommendation.priority_score)).where(
                CitationRecommendation.project_id == project_id,
                CitationRecommendation.tenant_id == tenant_id,
            )
        )
        avg_priority = avg_result.scalar() or 0

        # Competitor sites
        comp_result = await session.execute(
            select(func.count(func.distinct(CompetitorCitation.site_id))).where(
                CompetitorCitation.project_id == project_id,
                CompetitorCitation.site_id.isnot(None),
            )
        )
        competitor_sites = comp_result.scalar() or 0

        # Total sites available
        sites_result = await session.execute(
            select(func.count()).where(CitationSite.is_active == True)
        )
        total_sites = sites_result.scalar() or 0

        return APIResponse(
            data=RecommendationStats(
                total_sites=total_sites,
                recommended_count=total,
                accepted_count=accepted,
                competitor_sites=competitor_sites,
                avg_priority=round(float(avg_priority), 1),
            )
        )
