"""
SEO Platform — Citation Submissions API
=======================================
Endpoints for tracking individual citation submissions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.models.citation_v2 import (
    CitationProject,
    CitationSite,
    CitationSubmissionV2,
)
from seo_platform.schemas import APIResponse
from seo_platform.schemas.citation import (
    SubmissionBulkCreate,
    SubmissionCreate,
    SubmissionResponse,
    SubmissionStatusUpdate,
    SubmissionUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /citations/projects/{project_id}/submissions — List submissions
# ---------------------------------------------------------------------------
@router.get(
    "/projects/{project_id}/submissions",
    response_model=APIResponse[list[SubmissionResponse]],
)
async def list_submissions(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> APIResponse[list[SubmissionResponse]]:
    """List submissions for a project, with site info joined."""
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

        # Query submissions with site join
        query = (
            select(CitationSubmissionV2, CitationSite)
            .join(CitationSite, CitationSubmissionV2.site_id == CitationSite.id)
            .where(
                CitationSubmissionV2.project_id == project_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )

        if status:
            query = query.where(CitationSubmissionV2.status == status)

        # Count
        count_result = await session.execute(
            select(func.count()).select_from(
                select(CitationSubmissionV2.id)
                .where(
                    CitationSubmissionV2.project_id == project_id,
                    CitationSubmissionV2.tenant_id == tenant_id,
                    *([CitationSubmissionV2.status == status] if status else []),
                )
                .subquery()
            )
        )
        total = count_result.scalar() or 0

        # Paginate
        offset = (page - 1) * per_page
        query = query.order_by(CitationSite.difficulty_score.asc())
        query = query.offset(offset).limit(per_page)

        result = await session.execute(query)
        rows = result.all()

        responses = []
        for sub, site in rows:
            responses.append(SubmissionResponse(
                id=sub.id,
                project_id=sub.project_id,
                site_id=sub.site_id,
                site_name=site.name,
                site_url=site.url,
                site_category=site.category,
                site_difficulty=site.difficulty_score,
                site_da=site.domain_authority,
                status=sub.status,
                status_notes=sub.status_notes,
                account_created=sub.account_created,
                email_verified=sub.email_verified,
                listing_claimed=sub.listing_claimed,
                listing_url=sub.listing_url,
                started_at=sub.started_at,
                submitted_at=sub.submitted_at,
                completed_at=sub.completed_at,
                notes=sub.notes,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
            ))

        return APIResponse(
            data=responses,
            meta={"total": total, "offset": offset, "limit": per_page, "has_more": offset + per_page < total},
        )


# ---------------------------------------------------------------------------
# POST /citations/projects/{project_id}/submissions — Create submissions
# ---------------------------------------------------------------------------
@router.post(
    "/projects/{project_id}/submissions",
    response_model=APIResponse[list[SubmissionResponse]],
)
async def create_submissions(
    project_id: uuid.UUID,
    request: SubmissionCreate,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[SubmissionResponse]]:
    """Create a single submission entry for a site."""
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

        # Verify site exists
        site_result = await session.execute(
            select(CitationSite).where(
                CitationSite.id == request.site_id,
                CitationSite.tenant_id == tenant_id,
            )
        )
        site = site_result.scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        # Check for duplicate
        existing = await session.execute(
            select(CitationSubmissionV2).where(
                CitationSubmissionV2.project_id == project_id,
                CitationSubmissionV2.site_id == request.site_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Submission already exists for this site")

        submission = CitationSubmissionV2(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            site_id=request.site_id,
            status=request.status,
            notes=request.notes,
        )
        session.add(submission)
        await session.flush()

        resp = SubmissionResponse(
            id=submission.id,
            project_id=submission.project_id,
            site_id=submission.site_id,
            site_name=site.name,
            site_url=site.url,
            site_category=site.category,
            site_difficulty=site.difficulty_score,
            site_da=site.domain_authority,
            status=submission.status,
            notes=submission.notes,
            created_at=submission.created_at,
        )
        return APIResponse(data=[resp])


# ---------------------------------------------------------------------------
# POST /citations/projects/{project_id}/submissions/bulk — Bulk create
# ---------------------------------------------------------------------------
@router.post(
    "/projects/{project_id}/submissions/bulk",
    response_model=APIResponse[list[SubmissionResponse]],
)
async def bulk_create_submissions(
    project_id: uuid.UUID,
    request: SubmissionBulkCreate,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[SubmissionResponse]]:
    """Bulk-create submissions for multiple sites at once."""
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

        # Get existing submissions
        existing_result = await session.execute(
            select(CitationSubmissionV2.site_id).where(
                CitationSubmissionV2.project_id == project_id,
                CitationSubmissionV2.site_id.in_(request.site_ids),
            )
        )
        existing_site_ids = {row[0] for row in existing_result.all()}

        # Get sites
        sites_result = await session.execute(
            select(CitationSite).where(
                CitationSite.id.in_(request.site_ids),
                CitationSite.tenant_id == tenant_id,
            )
        )
        sites_map = {s.id: s for s in sites_result.scalars().all()}

        created = []
        for site_id in request.site_ids:
            if site_id in existing_site_ids:
                continue
            site = sites_map.get(site_id)
            if not site:
                continue

            submission = CitationSubmissionV2(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                project_id=project_id,
                site_id=site_id,
                status=request.status,
            )
            session.add(submission)
            created.append(SubmissionResponse(
                id=submission.id,
                project_id=project_id,
                site_id=site_id,
                site_name=site.name,
                site_url=site.url,
                site_category=site.category,
                site_difficulty=site.difficulty_score,
                site_da=site.domain_authority,
                status=request.status,
                created_at=submission.created_at,
            ))

        await session.flush()
        return APIResponse(data=created)


# ---------------------------------------------------------------------------
# PATCH /citations/submissions/{submission_id} — Update submission
# ---------------------------------------------------------------------------
@router.patch(
    "/submissions/{submission_id}",
    response_model=APIResponse[SubmissionResponse],
)
async def update_submission(
    submission_id: uuid.UUID,
    request: SubmissionUpdate,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[SubmissionResponse]:
    """Update submission details."""
    async with get_session() as session:
        result = await session.execute(
            select(CitationSubmissionV2, CitationSite)
            .join(CitationSite, CitationSubmissionV2.site_id == CitationSite.id)
            .where(
                CitationSubmissionV2.id == submission_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )
        row = result.one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Submission not found")

        sub, site = row
        update_data = request.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(sub, field, value)

        # Set timestamp based on status
        if "status" in update_data:
            now = datetime.now(UTC)
            if update_data["status"] == "in_progress" and not sub.started_at:
                sub.started_at = now
            elif update_data["status"] in ("already_exists", "new_backlink") and not sub.completed_at:
                sub.completed_at = now

        sub.updated_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(sub)

        resp = SubmissionResponse(
            id=sub.id,
            project_id=sub.project_id,
            site_id=sub.site_id,
            site_name=site.name,
            site_url=site.url,
            site_category=site.category,
            site_difficulty=site.difficulty_score,
            site_da=site.domain_authority,
            status=sub.status,
            status_notes=sub.status_notes,
            account_created=sub.account_created,
            email_verified=sub.email_verified,
            listing_claimed=sub.listing_claimed,
            listing_url=sub.listing_url,
            started_at=sub.started_at,
            submitted_at=sub.submitted_at,
            completed_at=sub.completed_at,
            notes=sub.notes,
            created_at=sub.created_at,
            updated_at=sub.updated_at,
        )
        return APIResponse(data=resp)


# ---------------------------------------------------------------------------
# PATCH /citations/submissions/{submission_id}/status — Quick status update
# ---------------------------------------------------------------------------
@router.patch(
    "/submissions/{submission_id}/status",
    response_model=APIResponse[SubmissionResponse],
)
async def update_submission_status(
    submission_id: uuid.UUID,
    request: SubmissionStatusUpdate,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[SubmissionResponse]:
    """Quick status update for a submission."""
    async with get_session() as session:
        result = await session.execute(
            select(CitationSubmissionV2, CitationSite)
            .join(CitationSite, CitationSubmissionV2.site_id == CitationSite.id)
            .where(
                CitationSubmissionV2.id == submission_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )
        row = result.one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Submission not found")

        sub, site = row
        now = datetime.now(UTC)

        sub.status = request.status
        if request.status_notes:
            sub.status_notes = request.status_notes
        if request.listing_url:
            sub.listing_url = request.listing_url
        if request.account_created is not None:
            sub.account_created = request.account_created
        if request.email_verified is not None:
            sub.email_verified = request.email_verified
        if request.listing_claimed is not None:
            sub.listing_claimed = request.listing_claimed
        if request.notes:
            sub.notes = request.notes

        # Set timestamps
        if request.status == "in_progress" and not sub.started_at:
            sub.started_at = now
        elif request.status in ("already_exists", "new_backlink") and not sub.completed_at:
            sub.completed_at = now

        sub.updated_at = now
        await session.flush()
        await session.refresh(sub)

        resp = SubmissionResponse(
            id=sub.id,
            project_id=sub.project_id,
            site_id=sub.site_id,
            site_name=site.name,
            site_url=site.url,
            site_category=site.category,
            site_difficulty=site.difficulty_score,
            site_da=site.domain_authority,
            status=sub.status,
            status_notes=sub.status_notes,
            account_created=sub.account_created,
            email_verified=sub.email_verified,
            listing_claimed=sub.listing_claimed,
            listing_url=sub.listing_url,
            started_at=sub.started_at,
            submitted_at=sub.submitted_at,
            completed_at=sub.completed_at,
            notes=sub.notes,
            created_at=sub.created_at,
            updated_at=sub.updated_at,
        )
        return APIResponse(data=resp)


# ---------------------------------------------------------------------------
# POST /citations/projects/{project_id}/submissions/auto-discover
# ---------------------------------------------------------------------------
@router.post(
    "/projects/{project_id}/submissions/auto-discover",
    response_model=APIResponse[list[SubmissionResponse]],
)
async def auto_discover_and_initialize(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[SubmissionResponse]]:
    """
    Auto-discover relevant sites and create submission entries.
    Combines discovery + initialization in one call.
    """
    async with get_session() as session:
        # Get project
        proj_result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get existing submissions
        existing_result = await session.execute(
            select(CitationSubmissionV2.site_id).where(
                CitationSubmissionV2.project_id == project_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )
        existing_site_ids = {row[0] for row in existing_result.all()}

        # Find matching sites
        site_query = select(CitationSite).where(
            CitationSite.tenant_id == tenant_id,
            CitationSite.is_active == True,
        )
        if project.category:
            site_query = site_query.where(CitationSite.category == project.category)
        site_query = site_query.where(CitationSite.geo_target.in_(["Australia", "Global", None]))
        if existing_site_ids:
            site_query = site_query.where(CitationSite.id.notin_(existing_site_ids))
        site_query = site_query.order_by(CitationSite.difficulty_score.asc())

        sites_result = await session.execute(site_query)
        sites = sites_result.scalars().all()

        created = []
        for site in sites:
            submission = CitationSubmissionV2(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                project_id=project_id,
                site_id=site.id,
                status="not_started",
            )
            session.add(submission)
            created.append(SubmissionResponse(
                id=submission.id,
                project_id=project_id,
                site_id=site.id,
                site_name=site.name,
                site_url=site.url,
                site_category=site.category,
                site_difficulty=site.difficulty_score,
                site_da=site.domain_authority,
                status="not_started",
                created_at=submission.created_at,
            ))

        # Update project total
        project.total_sites = len(existing_site_ids) + len(created)
        project.updated_at = datetime.now(UTC)
        await session.flush()

        logger.info(
            "citation_auto_discover_initialized",
            project_id=str(project_id),
            sites_added=len(created),
        )

        return APIResponse(data=created)
