"""
SEO Platform — Failure Recovery API
====================================
Endpoints for listing and retrying failed items across the platform.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text

from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /recovery/failed — List all failed items
# ---------------------------------------------------------------------------
@router.get("/failed")
async def list_failed_items(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """List all failed citation submissions and locked credentials."""
    async with get_session() as session:
        # Failed citation submissions
        subs = await session.execute(
            text("""
                SELECT s.id, s.status, s.status_notes, s.site_id, cs.name AS site_name,
                       s.project_id, cp.business_name, s.updated_at
                FROM citation_submissions s
                JOIN citation_sites cs ON s.site_id = cs.id
                JOIN citation_projects cp ON s.project_id = cp.id
                WHERE s.tenant_id = :tid AND s.status IN ('failed', 'rejected')
                ORDER BY s.updated_at DESC
            """),
            {"tid": str(user.tenant_id)},
        )
        failed_subs = [
            {
                "type": "submission",
                "id": str(r.id),
                "name": r.site_name,
                "project": r.business_name,
                "status": r.status,
                "error": r.status_notes,
                "updated_at": str(r.updated_at),
            }
            for r in subs.fetchall()
        ]

        # Failed credentials (locked)
        creds = await session.execute(
            text("""
                SELECT id, site_slug, status, failure_count, last_failure_reason, updated_at
                FROM directory_credentials
                WHERE tenant_id = :tid AND status = 'locked'
            """),
            {"tid": str(user.tenant_id)},
        )
        failed_creds = [
            {
                "type": "credential",
                "id": str(r.id),
                "name": r.site_slug,
                "status": r.status,
                "error": r.last_failure_reason,
                "count": r.failure_count,
                "updated_at": str(r.updated_at),
            }
            for r in creds.fetchall()
        ]

    return APIResponse(
        data={
            "submissions": failed_subs,
            "credentials": failed_creds,
            "total": len(failed_subs) + len(failed_creds),
        }
    )


# ---------------------------------------------------------------------------
# POST /recovery/retry/{item_type}/{item_id} — Retry a single failed item
# ---------------------------------------------------------------------------
@router.post("/retry/{item_type}/{item_id}")
async def retry_item(
    item_type: str,
    item_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Reset a failed item's status so it can be retried."""
    async with get_session() as session:
        if item_type == "submission":
            await session.execute(
                text("""
                    UPDATE citation_submissions
                    SET status = 'pending', status_notes = NULL, updated_at = NOW()
                    WHERE id = :id AND tenant_id = :tid
                """),
                {"id": str(item_id), "tid": str(user.tenant_id)},
            )
        elif item_type == "credential":
            await session.execute(
                text("""
                    UPDATE directory_credentials
                    SET status = 'active', failure_count = 0, last_error = NULL, updated_at = NOW()
                    WHERE id = :id AND tenant_id = :tid
                """),
                {"id": str(item_id), "tid": str(user.tenant_id)},
            )
        else:
            return APIResponse(data={"retried": False}, error=f"Unknown item type: {item_type}")

        await session.commit()

    logger.info("recovery_retry_item", item_type=item_type, item_id=str(item_id))
    return APIResponse(data={"retried": True})


# ---------------------------------------------------------------------------
# POST /recovery/retry-all — Reset all failed items
# ---------------------------------------------------------------------------
@router.post("/retry-all")
async def retry_all_failed(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Reset all failed submissions and locked credentials."""
    async with get_session() as session:
        sub_result = await session.execute(
            text("""
                UPDATE citation_submissions
                SET status = 'pending', status_notes = NULL, updated_at = NOW()
                WHERE tenant_id = :tid AND status IN ('failed', 'rejected')
            """),
            {"tid": str(user.tenant_id)},
        )
        cred_result = await session.execute(
            text("""
                UPDATE directory_credentials
                SET status = 'active', failure_count = 0, last_error = NULL, updated_at = NOW()
                WHERE tenant_id = :tid AND status = 'locked'
            """),
            {"tid": str(user.tenant_id)},
        )
        await session.commit()

    logger.info(
        "recovery_retry_all",
        retried_submissions=sub_result.rowcount,
        retried_credentials=cred_result.rowcount,
    )
    return APIResponse(
        data={
            "retried_submissions": sub_result.rowcount,
            "retried_credentials": cred_result.rowcount,
        }
    )
