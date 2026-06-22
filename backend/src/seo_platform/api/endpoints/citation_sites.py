"""
SEO Platform — Citation Sites API
=================================
Endpoints for listing and discovering citation sites.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.models.citation_v2 import CitationSite, CitationSubmissionV2
from seo_platform.schemas import APIResponse
from seo_platform.schemas.citation import CitationSiteResponse

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /citations/sites — List all sites (filterable)
# ---------------------------------------------------------------------------
@router.get("", response_model=APIResponse[list[CitationSiteResponse]])
@router.get("/", response_model=APIResponse[list[CitationSiteResponse]])
async def list_sites(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
    category: str | None = Query(None, description="Filter by category"),
    niche: str | None = Query(None, description="Filter by niche"),
    geo_target: str | None = Query(None, description="Filter by geo target"),
    region: str | None = Query(None, description="Filter by region (AU, US, UK, CA, EU, APAC, global)"),
    difficulty_min: int | None = Query(None, ge=0, le=100),
    difficulty_max: int | None = Query(None, ge=0, le=100),
    has_logo_upload: bool | None = Query(None),
    has_email_verification: bool | None = Query(None),
    is_premium: bool | None = Query(None, description="Filter by premium status"),
    importance_min: int | None = Query(None, ge=0, le=100),
    importance_max: int | None = Query(None, ge=0, le=100),
    search: str | None = Query(None, description="Search by site name"),
    sort_by: str = Query("importance_score", description="Sort field: importance_score, name, difficulty_score"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> APIResponse[list[CitationSiteResponse]]:
    """List all citation sites with optional filtering."""
    async with get_session() as session:
        query = select(CitationSite).where(
            CitationSite.tenant_id == tenant_id,
            CitationSite.is_active == True,
        )

        if category:
            query = query.where(CitationSite.category == category)
        if niche:
            query = query.where(CitationSite.niche == niche)
        if geo_target:
            query = query.where(CitationSite.geo_target == geo_target)
        if region:
            query = query.where(CitationSite.region == region)
        if difficulty_min is not None:
            query = query.where(CitationSite.difficulty_score >= difficulty_min)
        if difficulty_max is not None:
            query = query.where(CitationSite.difficulty_score <= difficulty_max)
        if has_logo_upload is not None:
            query = query.where(CitationSite.has_logo_upload == has_logo_upload)
        if has_email_verification is not None:
            query = query.where(CitationSite.requires_email_verification == has_email_verification)
        if is_premium is not None:
            query = query.where(CitationSite.is_premium == is_premium)
        if importance_min is not None:
            query = query.where(CitationSite.importance_score >= importance_min)
        if importance_max is not None:
            query = query.where(CitationSite.importance_score <= importance_max)
        if search:
            query = query.where(CitationSite.name.ilike(f"%{search}%"))

        # Count
        count_result = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Sort
        sort_column = {
            "importance_score": CitationSite.importance_score,
            "name": CitationSite.name,
            "difficulty_score": CitationSite.difficulty_score,
        }.get(sort_by, CitationSite.importance_score)
        
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Paginate
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        result = await session.execute(query)
        sites = result.scalars().all()

        return APIResponse(
            data=[CitationSiteResponse.model_validate(s) for s in sites],
            meta={"total": total, "offset": offset, "limit": per_page, "has_more": offset + per_page < total},
        )


# ---------------------------------------------------------------------------
# GET /citations/sites/{site_id} — Get single site
# ---------------------------------------------------------------------------
@router.get("/{site_id}", response_model=APIResponse[CitationSiteResponse])
async def get_site(
    site_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CitationSiteResponse]:
    """Get a single citation site by ID."""
    async with get_session() as session:
        result = await session.execute(
            select(CitationSite).where(
                CitationSite.id == site_id,
                CitationSite.tenant_id == tenant_id,
            )
        )
        site = result.scalar_one_or_none()
        if not site:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Site not found")
        return APIResponse(data=CitationSiteResponse.model_validate(site))


# ---------------------------------------------------------------------------
# GET /citations/sites/for-project/{project_id} — Discovery
# ---------------------------------------------------------------------------
@router.get("/for-project/{project_id}", response_model=APIResponse[list[CitationSiteResponse]])
async def sites_for_project(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
    region: str | None = Query(None, description="Filter by region"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> APIResponse[list[CitationSiteResponse]]:
    """
    Get sites recommended for a project based on category, keywords, and geo.
    Excludes sites already in submissions for this project.
    """
    from seo_platform.models.citation_v2 import CitationProject

    async with get_session() as session:
        # Get project details
        proj_result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Project not found")

        # Get existing submission site IDs
        existing_result = await session.execute(
            select(CitationSubmissionV2.site_id).where(
                CitationSubmissionV2.project_id == project_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )
        existing_site_ids = {row[0] for row in existing_result.all()}

        # Build site query
        query = select(CitationSite).where(
            CitationSite.tenant_id == tenant_id,
            CitationSite.is_active == True,
        )

        # Match category
        if project.category:
            query = query.where(CitationSite.category == project.category)

        # Match geo (Australia + Global + region-specific)
        geo_targets = ["Australia", "Global", None]
        if region:
            query = query.where(CitationSite.region == region)
        else:
            query = query.where(CitationSite.geo_target.in_(geo_targets))

        # Exclude existing
        if existing_site_ids:
            query = query.where(CitationSite.id.notin_(existing_site_ids))

        # Count
        count_result = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        offset = (page - 1) * per_page
        query = query.order_by(CitationSite.importance_score.desc())
        query = query.offset(offset).limit(per_page)

        result = await session.execute(query)
        sites = result.scalars().all()

        return APIResponse(
            data=[CitationSiteResponse.model_validate(s) for s in sites],
            meta={"total": total, "offset": offset, "limit": per_page, "has_more": offset + per_page < total},
        )
