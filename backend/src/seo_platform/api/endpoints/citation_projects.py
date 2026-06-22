"""
SEO Platform — Citation Projects API
====================================
CRUD endpoints for citation projects.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_session
from seo_platform.core.encryption import encryption_service
from seo_platform.core.logging import get_logger
from seo_platform.models.citation_v2 import CitationProject, CitationSite, CitationSubmissionV2
from seo_platform.schemas import APIResponse
from seo_platform.schemas.citation import (
    CitationProjectCreate,
    CitationProjectResponse,
    CitationProjectStats,
    CitationProjectUpdate,
    DiscoveryResult,
)

logger = get_logger(__name__)
router = APIRouter()


async def _get_project_or_404(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> CitationProject:
    """Fetch a citation project by ID + tenant_id, or raise 404."""
    result = await session.execute(
        select(CitationProject).where(
            CitationProject.id == project_id,
            CitationProject.tenant_id == tenant_id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _compute_stats(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> CitationProjectStats:
    """Compute submission stats for a project."""
    result = await session.execute(
        select(
            CitationSubmissionV2.status,
            func.count(CitationSubmissionV2.id),
        ).where(
            CitationSubmissionV2.project_id == project_id,
            CitationSubmissionV2.tenant_id == tenant_id,
        ).group_by(CitationSubmissionV2.status)
    )
    counts = {row[0]: row[1] for row in result.all()}
    total = sum(counts.values())
    completed = counts.get("already_exists", 0) + counts.get("new_backlink", 0)
    completion_pct = (completed / total * 100) if total > 0 else 0.0

    return CitationProjectStats(
        total_sites=total,
        pending=counts.get("not_started", 0) + counts.get("pending", 0),
        in_progress=counts.get("in_progress", 0),
        already_exists=counts.get("already_exists", 0),
        new_backlink=counts.get("new_backlink", 0),
        failed=counts.get("failed", 0),
        rejected=counts.get("rejected", 0),
        completion_pct=round(completion_pct, 1),
    )


# ---------------------------------------------------------------------------
# POST /citations/projects — Create project
# ---------------------------------------------------------------------------
@router.post("/projects", response_model=APIResponse[CitationProjectResponse])
async def create_project(
    request: CitationProjectCreate,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CitationProjectResponse]:
    """Create a new citation project."""
    tenant_id = user.tenant_id
    async with get_session() as session:
        # Encrypt submission password if provided
        encrypted_password = None
        if request.submission_password:
            encrypted_password = encryption_service.encrypt(request.submission_password)

        project = CitationProject(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=request.client_id,
            business_name=request.business_name,
            website_url=request.website_url,
            category=request.category,
            keywords=request.keywords or [],
            phone=request.phone,
            email=request.email,
            description=request.description,
            short_bio=request.short_bio,
            long_bio=request.long_bio,
            address=request.address,
            city=request.city,
            state=request.state,
            country=request.country,
            postal_code=request.postal_code,
            hours_mon=request.hours_mon,
            hours_tue=request.hours_tue,
            hours_wed=request.hours_wed,
            hours_thu=request.hours_thu,
            hours_fri=request.hours_fri,
            hours_sat=request.hours_sat,
            hours_sun=request.hours_sun,
            logo_url=request.logo_url,
            facebook_url=request.facebook_url,
            twitter_url=request.twitter_url,
            linkedin_url=request.linkedin_url,
            instagram_url=request.instagram_url,
            youtube_url=request.youtube_url,
            pinterest_url=request.pinterest_url,
            submission_email=request.submission_email,
            submission_password=encrypted_password,
            status="active",
        )
        session.add(project)
        await session.flush()
        await session.refresh(project)

        logger.info("citation_project_created", project_id=str(project.id), tenant_id=str(tenant_id))

        response = CitationProjectResponse.model_validate(project)
        response.stats = CitationProjectStats()
        return APIResponse(data=response)


# ---------------------------------------------------------------------------
# GET /citations/projects — List projects
# ---------------------------------------------------------------------------
@router.get("/projects", response_model=APIResponse[list[CitationProjectResponse]])
async def list_projects(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by business name"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> APIResponse[list[CitationProjectResponse]]:
    """List citation projects for the tenant."""
    async with get_session() as session:
        query = select(CitationProject).where(CitationProject.tenant_id == tenant_id)

        if status:
            query = query.where(CitationProject.status == status)
        if search:
            query = query.where(
                CitationProject.business_name.ilike(f"%{search}%")
            )

        # Count
        count_result = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginate
        offset = (page - 1) * per_page
        query = query.order_by(CitationProject.created_at.desc())
        query = query.offset(offset).limit(per_page)

        result = await session.execute(query)
        projects = result.scalars().all()

        responses = []
        for project in projects:
            resp = CitationProjectResponse.model_validate(project)
            resp.stats = await _compute_stats(project.id, tenant_id, session)
            responses.append(resp)

        return APIResponse(
            data=responses,
            meta={"total": total, "offset": offset, "limit": per_page, "has_more": offset + per_page < total},
        )


# ---------------------------------------------------------------------------
# GET /citations/projects/{project_id} — Get single project
# ---------------------------------------------------------------------------
@router.get("/projects/{project_id}", response_model=APIResponse[CitationProjectResponse])
async def get_project(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CitationProjectResponse]:
    """Get a single citation project by ID."""
    async with get_session() as session:
        project = await _get_project_or_404(project_id, tenant_id, session)
        resp = CitationProjectResponse.model_validate(project)
        resp.stats = await _compute_stats(project.id, tenant_id, session)
        return APIResponse(data=resp)


# ---------------------------------------------------------------------------
# PUT /citations/projects/{project_id} — Update project
# ---------------------------------------------------------------------------
@router.put("/projects/{project_id}", response_model=APIResponse[CitationProjectResponse])
async def update_project(
    project_id: uuid.UUID,
    request: CitationProjectUpdate,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CitationProjectResponse]:
    """Update a citation project."""
    async with get_session() as session:
        project = await _get_project_or_404(project_id, tenant_id, session)

        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Encrypt password if being updated
        if "submission_password" in update_data and update_data["submission_password"]:
            update_data["submission_password"] = encryption_service.encrypt(
                update_data["submission_password"]
            )

        for field, value in update_data.items():
            setattr(project, field, value)

        project.updated_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(project)

        logger.info("citation_project_updated", project_id=str(project_id))

        resp = CitationProjectResponse.model_validate(project)
        resp.stats = await _compute_stats(project.id, tenant_id, session)
        return APIResponse(data=resp)


# ---------------------------------------------------------------------------
# DELETE /citations/projects/{project_id} — Delete project
# ---------------------------------------------------------------------------
@router.delete("/projects/{project_id}", response_model=APIResponse[None])
async def delete_project(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[None]:
    """Delete a citation project and its submissions."""
    async with get_session() as session:
        project = await _get_project_or_404(project_id, tenant_id, session)
        await session.delete(project)
        await session.flush()
        logger.info("citation_project_deleted", project_id=str(project_id))
        return APIResponse(data=None)


# ---------------------------------------------------------------------------
# PATCH /citations/projects/{project_id}/status — Update status
# ---------------------------------------------------------------------------
@router.patch("/projects/{project_id}/status", response_model=APIResponse[CitationProjectResponse])
async def update_project_status(
    project_id: uuid.UUID,
    status: str = Query(..., description="New status"),
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CitationProjectResponse]:
    """Update a project's status."""
    valid_statuses = {"active", "paused", "completed", "archived"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    async with get_session() as session:
        project = await _get_project_or_404(project_id, tenant_id, session)
        project.status = status
        project.updated_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(project)

        logger.info("citation_project_status_updated", project_id=str(project_id), status=status)

        resp = CitationProjectResponse.model_validate(project)
        resp.stats = await _compute_stats(project.id, tenant_id, session)
        return APIResponse(data=resp)


# ---------------------------------------------------------------------------
# POST /citations/projects/{project_id}/discover — Discover & add sites
# ---------------------------------------------------------------------------
@router.post("/projects/{project_id}/discover", response_model=APIResponse[DiscoveryResult])
async def discover_sites(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[DiscoveryResult]:
    """
    Auto-discover relevant citation sites for a project and create
    submission entries for sites not yet tracked.
    """
    async with get_session() as session:
        project = await _get_project_or_404(project_id, tenant_id, session)

        # Find sites already submitted for this project
        existing_result = await session.execute(
            select(CitationSubmissionV2.site_id).where(
                CitationSubmissionV2.project_id == project_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )
        existing_site_ids = {row[0] for row in existing_result.all()}

        # Query matching sites
        site_query = select(CitationSite).where(
            CitationSite.tenant_id == tenant_id,
            CitationSite.is_active == True,
        )

        # Match by category if project has one
        if project.category:
            site_query = site_query.where(
                CitationSite.category == project.category
            )

        # Match by geo_target (Australia + Global)
        site_query = site_query.where(
            CitationSite.geo_target.in_(["Australia", "Global", None])
        )

        # Exclude already-tracked sites
        if existing_site_ids:
            site_query = site_query.where(CitationSite.id.notin_(existing_site_ids))

        # Order by difficulty ascending (easiest first)
        site_query = site_query.order_by(CitationSite.difficulty_score.asc())

        result = await session.execute(site_query)
        available_sites = result.scalars().all()

        # Create submissions for discovered sites
        added = 0
        for site in available_sites:
            submission = CitationSubmissionV2(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                project_id=project_id,
                site_id=site.id,
                status="not_started",
            )
            session.add(submission)
            added += 1

        # Update project counters
        project.total_sites = len(existing_site_ids) + added
        project.updated_at = datetime.now(UTC)
        await session.flush()

        logger.info(
            "citation_sites_discovered",
            project_id=str(project_id),
            sites_added=added,
            total_available=len(available_sites),
        )

        return APIResponse(
            data=DiscoveryResult(
                sites_added=added,
                sites_already_tracked=len(existing_site_ids),
                total_available=len(available_sites) + len(existing_site_ids),
            )
        )
