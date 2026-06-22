"""
SEO Platform — Citation Operations Engine
==========================================
Centralized operational view of all citation submissions: status tracking,
retry management, verification workflows, and analytics by site category.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_

from seo_platform.core.auth import CurrentUser, get_validated_tenant_id
from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.rbac import RequirePermission
from seo_platform.models.citation_v2 import (
    CitationProject,
    CitationSite,
    CitationSubmissionV2,
)
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)

router = APIRouter()

# Valid submission lifecycle transitions
VALID_SUBMISSION_TRANSITIONS: dict[str, list[str]] = {
    "not_started": ["in_progress"],
    "in_progress": ["new_backlink", "already_exists", "failed"],
    "failed": ["in_progress"],
    "new_backlink": ["verified"],
    "already_exists": [],
    "pending": ["in_progress"],
    "pending_review": ["in_progress", "new_backlink", "failed"],
    "rejected": ["in_progress"],
    "verified": [],
}


def _enum_val(val: Any) -> str:
    return val.value if hasattr(val, "value") else str(val)


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------
class SubmissionSummary(BaseModel):
    id: str
    project_id: str
    site_id: str
    site_name: str | None = None
    site_url: str | None = None
    site_category: str | None = None
    site_difficulty: int | None = None
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    listing_url: str | None = None


class CitationDashboard(BaseModel):
    total_submissions: int
    by_status: dict[str, int]
    success_rate: float
    needs_retry_count: int
    needs_verification_count: int
    needs_retry_submissions: list[SubmissionSummary]
    needs_verification_submissions: list[SubmissionSummary]


class ProjectSubmissionsResponse(BaseModel):
    project_id: str
    project_name: str
    total: int
    by_status: dict[str, int]
    submissions: list[SubmissionSummary]


class RetryResponse(BaseModel):
    submission_id: str
    new_status: str
    message: str


class BulkRetryResponse(BaseModel):
    retries_created: int
    submission_ids: list[str]


class CategoryRate(BaseModel):
    category: str
    total: int
    successful: int
    success_rate: float


class DifficultyRate(BaseModel):
    difficulty: str
    total: int
    successful: int
    success_rate: float


class CitationAnalytics(BaseModel):
    overall_success_rate: float
    total_submissions: int
    total_successful: int
    success_rates_by_category: list[CategoryRate]
    success_rates_by_difficulty: list[DifficultyRate]
    avg_days_to_verification: float | None = None
    nap_consistency_score: float | None = None


# ---------------------------------------------------------------------------
# GET /citation-operations/dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_model=APIResponse[CitationDashboard])
async def get_citation_dashboard(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
) -> APIResponse[CitationDashboard]:
    """Full citation operations dashboard with status counts, retry and verification alerts."""
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(CitationSubmissionV2)
            .where(CitationSubmissionV2.tenant_id == tenant_id)
        )
        submissions = result.scalars().all()

        # Status counts
        by_status: dict[str, int] = {}
        for s in submissions:
            status_str = s.status if isinstance(s.status, str) else str(s.status)
            by_status[status_str] = by_status.get(status_str, 0) + 1

        # Success rate: new_backlink + already_exists / total
        total = len(submissions)
        successful = sum(
            1 for s in submissions
            if (s.status if isinstance(s.status, str) else str(s.status))
            in ("new_backlink", "already_exists", "verified")
        )
        success_rate = round(successful / max(total, 1), 4)

        # Needs retry (failed submissions)
        failed_submissions = [
            s for s in submissions
            if (s.status if isinstance(s.status, str) else str(s.status)) == "failed"
        ]

        # Needs verification (new_backlink not yet verified)
        needs_verification = [
            s for s in submissions
            if (s.status if isinstance(s.status, str) else str(s.status)) == "new_backlink"
        ]

        # Enrich with site info
        site_ids = {s.site_id for s in submissions}
        if site_ids:
            sites_result = await session.execute(
                select(CitationSite).where(
                    CitationSite.id.in_(site_ids),
                    CitationSite.tenant_id == tenant_id,
                )
            )
            sites_map = {s.id: s for s in sites_result.scalars().all()}
        else:
            sites_map = {}

        def _to_summary(sub: CitationSubmissionV2) -> SubmissionSummary:
            site = sites_map.get(sub.site_id)
            return SubmissionSummary(
                id=str(sub.id),
                project_id=str(sub.project_id),
                site_id=str(sub.site_id),
                site_name=site.name if site else None,
                site_url=site.url if site else None,
                site_category=site.category if site else None,
                site_difficulty=site.difficulty_score if site else None,
                status=sub.status if isinstance(sub.status, str) else str(sub.status),
                started_at=sub.started_at.isoformat() if sub.started_at else None,
                completed_at=sub.completed_at.isoformat() if sub.completed_at else None,
                listing_url=sub.listing_url,
            )

        return APIResponse(
            data=CitationDashboard(
                total_submissions=total,
                by_status=by_status,
                success_rate=success_rate,
                needs_retry_count=len(failed_submissions),
                needs_verification_count=len(needs_verification),
                needs_retry_submissions=[_to_summary(s) for s in failed_submissions[:20]],
                needs_verification_submissions=[_to_summary(s) for s in needs_verification[:20]],
            )
        )


# ---------------------------------------------------------------------------
# GET /citation-operations/project/{project_id}/submissions
# ---------------------------------------------------------------------------
@router.get(
    "/project/{project_id}/submissions",
    response_model=APIResponse[ProjectSubmissionsResponse],
)
async def get_project_submissions(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
    status: str | None = Query(None, description="Filter by status"),
) -> APIResponse[ProjectSubmissionsResponse]:
    """All submissions for a project with site details, filterable by status."""
    async with get_tenant_session(tenant_id) as session:
        # Verify project
        proj_result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

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

        query = query.order_by(CitationSite.difficulty_score.asc())
        result = await session.execute(query)
        rows = result.all()

        by_status: dict[str, int] = {}
        submissions: list[SubmissionSummary] = []
        for sub, site in rows:
            s = sub.status if isinstance(sub.status, str) else str(sub.status)
            by_status[s] = by_status.get(s, 0) + 1
            submissions.append(SubmissionSummary(
                id=str(sub.id),
                project_id=str(sub.project_id),
                site_id=str(sub.site_id),
                site_name=site.name,
                site_url=site.url,
                site_category=site.category,
                site_difficulty=site.difficulty_score,
                status=s,
                started_at=sub.started_at.isoformat() if sub.started_at else None,
                completed_at=sub.completed_at.isoformat() if sub.completed_at else None,
                listing_url=sub.listing_url,
            ))

        return APIResponse(
            data=ProjectSubmissionsResponse(
                project_id=str(project_id),
                project_name=project.business_name,
                total=len(submissions),
                by_status=by_status,
                submissions=submissions,
            )
        )


# ---------------------------------------------------------------------------
# POST /citation-operations/submission/{submission_id}/retry
# ---------------------------------------------------------------------------
@router.post(
    "/submission/{submission_id}/retry",
    response_model=APIResponse[RetryResponse],
)
async def retry_submission(
    submission_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[RetryResponse]:
    """Retry a failed submission — resets status to in_progress."""
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(CitationSubmissionV2).where(
                CitationSubmissionV2.id == submission_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            raise HTTPException(status_code=404, detail="Submission not found")

        current_status = sub.status if isinstance(sub.status, str) else str(sub.status)
        if current_status != "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry submission in '{current_status}' status. Only 'failed' submissions can be retried.",
            )

        now = datetime.now(UTC)
        sub.status = "in_progress"
        sub.started_at = now
        sub.completed_at = None
        sub.updated_at = now
        sub.status_notes = f"Retried at {now.isoformat()}"

        await session.flush()

        logger.info("citation_submission_retried", submission_id=str(submission_id))

        return APIResponse(
            data=RetryResponse(
                submission_id=str(submission_id),
                new_status="in_progress",
                message="Submission reset to in_progress for retry.",
            )
        )


# ---------------------------------------------------------------------------
# POST /citation-operations/submission/{submission_id}/verify
# ---------------------------------------------------------------------------
@router.post(
    "/submission/{submission_id}/verify",
    response_model=APIResponse[SubmissionSummary],
)
async def verify_submission(
    submission_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[SubmissionSummary]:
    """Mark a new_backlink submission as verified."""
    async with get_tenant_session(tenant_id) as session:
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
        current_status = sub.status if isinstance(sub.status, str) else str(sub.status)
        if current_status != "new_backlink":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot verify submission in '{current_status}' status. Only 'new_backlink' submissions can be verified.",
            )

        now = datetime.now(UTC)
        sub.status = "verified"
        sub.completed_at = now
        sub.updated_at = now
        sub.listing_claimed = True
        sub.status_notes = f"Verified at {now.isoformat()}"

        await session.flush()
        await session.refresh(sub)

        logger.info("citation_submission_verified", submission_id=str(submission_id))

        return APIResponse(
            data=SubmissionSummary(
                id=str(sub.id),
                project_id=str(sub.project_id),
                site_id=str(sub.site_id),
                site_name=site.name,
                site_url=site.url,
                site_category=site.category,
                site_difficulty=site.difficulty_score,
                status="verified",
                started_at=sub.started_at.isoformat() if sub.started_at else None,
                completed_at=sub.completed_at.isoformat() if sub.completed_at else None,
                listing_url=sub.listing_url,
            )
        )


# ---------------------------------------------------------------------------
# POST /citation-operations/bulk-retry
# ---------------------------------------------------------------------------
@router.post(
    "/bulk-retry",
    response_model=APIResponse[BulkRetryResponse],
)
async def bulk_retry_failed(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    project_id: uuid.UUID | None = Query(None, description="Scope to specific project"),
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[BulkRetryResponse]:
    """Retry all failed submissions, optionally scoped to a project."""
    async with get_tenant_session(tenant_id) as session:
        query = select(CitationSubmissionV2).where(
            CitationSubmissionV2.tenant_id == tenant_id,
            CitationSubmissionV2.status == "failed",
        )
        if project_id:
            query = query.where(CitationSubmissionV2.project_id == project_id)

        result = await session.execute(query)
        failed = result.scalars().all()

        now = datetime.now(UTC)
        ids: list[str] = []
        for sub in failed:
            sub.status = "in_progress"
            sub.started_at = now
            sub.completed_at = None
            sub.updated_at = now
            sub.status_notes = f"Bulk retried at {now.isoformat()}"
            ids.append(str(sub.id))

        await session.flush()

        logger.info("citation_bulk_retry", count=len(ids), project_id=str(project_id) if project_id else None)

        return APIResponse(
            data=BulkRetryResponse(
                retries_created=len(ids),
                submission_ids=ids,
            )
        )


# ---------------------------------------------------------------------------
# GET /citation-operations/analytics
# ---------------------------------------------------------------------------
@router.get("/analytics", response_model=APIResponse[CitationAnalytics])
async def get_citation_analytics(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
) -> APIResponse[CitationAnalytics]:
    """Citation analytics: success rates by category and difficulty, verification time, NAP scores."""
    async with get_tenant_session(tenant_id) as session:
        # All submissions with sites
        result = await session.execute(
            select(CitationSubmissionV2, CitationSite)
            .join(CitationSite, CitationSubmissionV2.site_id == CitationSite.id)
            .where(CitationSubmissionV2.tenant_id == tenant_id)
        )
        rows = result.all()

        total = len(rows)
        successful_statuses = {"new_backlink", "already_exists", "verified"}
        successful = sum(
            1 for sub, _ in rows
            if (sub.status if isinstance(sub.status, str) else str(sub.status)) in successful_statuses
        )
        overall_success_rate = round(successful / max(total, 1), 4)

        # By category
        category_data: dict[str, dict[str, int]] = {}
        for sub, site in rows:
            cat = site.category or "unknown"
            category_data.setdefault(cat, {"total": 0, "successful": 0})
            category_data[cat]["total"] += 1
            if (sub.status if isinstance(sub.status, str) else str(sub.status)) in successful_statuses:
                category_data[cat]["successful"] += 1

        rates_by_category = [
            CategoryRate(
                category=cat,
                total=d["total"],
                successful=d["successful"],
                success_rate=round(d["successful"] / max(d["total"], 1), 4),
            )
            for cat, d in sorted(category_data.items(), key=lambda x: x[1]["total"], reverse=True)
        ]

        # By difficulty
        difficulty_data: dict[str, dict[str, int]] = {}
        for sub, site in rows:
            diff = site.submission_difficulty or "unknown"
            difficulty_data.setdefault(diff, {"total": 0, "successful": 0})
            difficulty_data[diff]["total"] += 1
            if (sub.status if isinstance(sub.status, str) else str(sub.status)) in successful_statuses:
                difficulty_data[diff]["successful"] += 1

        rates_by_difficulty = [
            DifficultyRate(
                difficulty=d,
                total=data["total"],
                successful=data["successful"],
                success_rate=round(data["successful"] / max(data["total"], 1), 4),
            )
            for d, data in sorted(difficulty_data.items())
        ]

        # Average time to verification
        verification_times: list[float] = []
        for sub, _ in rows:
            status = sub.status if isinstance(sub.status, str) else str(sub.status)
            if status == "verified" and sub.started_at and sub.completed_at:
                delta = (sub.completed_at - sub.started_at).total_seconds() / 86400
                verification_times.append(delta)

        avg_days = round(sum(verification_times) / len(verification_times), 1) if verification_times else None

        # NAP consistency: percentage of submissions with listing_url set among successful
        nap_count = sum(
            1 for sub, _ in rows
            if (sub.status if isinstance(sub.status, str) else str(sub.status)) in successful_statuses
            and sub.listing_url
        )
        nap_score = round(nap_count / max(successful, 1), 4) if successful > 0 else None

        return APIResponse(
            data=CitationAnalytics(
                overall_success_rate=overall_success_rate,
                total_submissions=total,
                total_successful=successful,
                success_rates_by_category=rates_by_category,
                success_rates_by_difficulty=rates_by_difficulty,
                avg_days_to_verification=avg_days,
                nap_consistency_score=nap_score,
            )
        )
