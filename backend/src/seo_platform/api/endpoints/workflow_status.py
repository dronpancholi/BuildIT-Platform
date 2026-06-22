from fastapi import APIRouter, Depends
from sqlalchemy import text
from seo_platform.core.database import get_session
from seo_platform.core.auth import CurrentUser, get_current_user

router = APIRouter()


@router.get("/overview")
async def workflow_overview(user: CurrentUser = Depends(get_current_user)):
    """Get overview of all active workflows with status, progress, and next actions."""
    async with get_session() as session:
        # Active campaigns (table is backlink_campaigns)
        campaigns = await session.execute(
            text(
                """
                SELECT id, name, status, created_at, updated_at
                FROM backlink_campaigns WHERE tenant_id = :tid AND status NOT IN ('archived', 'cancelled')
                ORDER BY updated_at DESC LIMIT 20
                """
            ),
            {"tid": str(user.tenant_id)},
        )
        campaign_list = []
        for r in campaigns.fetchall():
            progress = 0
            next_action = "No action needed"
            if r.status == "draft":
                next_action = "Launch campaign"
            elif r.status == "active":
                next_action = "Monitor progress"
            elif r.status == "paused":
                next_action = "Resume campaign"

            campaign_list.append(
                {
                    "id": str(r.id),
                    "type": "campaign",
                    "name": r.name,
                    "status": r.status,
                    "progress": progress,
                    "started": str(r.created_at),
                    "updated": str(r.updated_at),
                    "next_action": next_action,
                }
            )

        # Active citation projects
        citations = await session.execute(
            text(
                """
                SELECT id, business_name, status, created_at, updated_at
                FROM citation_projects WHERE tenant_id = :tid AND status NOT IN ('archived', 'completed')
                ORDER BY updated_at DESC LIMIT 20
                """
            ),
            {"tid": str(user.tenant_id)},
        )
        citation_list = []
        for r in citations.fetchall():
            sub_count = await session.execute(
                text("SELECT COUNT(*) FROM citation_submissions WHERE project_id = :pid"),
                {"pid": str(r.id)},
            )
            done_count = await session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM citation_submissions
                    WHERE project_id = :pid AND status IN ('already_exists', 'not_started', 'in_progress', 'pending_review')
                    """
                ),
                {"pid": str(r.id)},
            )
            tc = sub_count.scalar() or 0
            dc = done_count.scalar() or 0
            progress = round((dc / tc * 100) if tc > 0 else 0)

            next_action = "Add sites to project"
            if tc > 0 and dc < tc:
                next_action = f"Process {tc - dc} remaining submissions"
            elif tc > 0 and dc >= tc:
                next_action = "All submissions processed"

            citation_list.append(
                {
                    "id": str(r.id),
                    "type": "citation_project",
                    "name": r.business_name,
                    "status": r.status,
                    "progress": progress,
                    "started": str(r.created_at),
                    "updated": str(r.updated_at),
                    "next_action": next_action,
                }
            )

        # Pending approvals
        approvals = await session.execute(
            text(
                """
                SELECT id, category, status, created_at, updated_at
                FROM approval_requests WHERE tenant_id = :tid AND status = 'pending'
                ORDER BY created_at DESC LIMIT 10
                """
            ),
            {"tid": str(user.tenant_id)},
        )
        approval_list = []
        for r in approvals.fetchall():
            approval_list.append(
                {
                    "id": str(r.id),
                    "type": "approval",
                    "name": f"{r.category} approval",
                    "status": r.status,
                    "progress": 0,
                    "started": str(r.created_at),
                    "updated": str(r.updated_at),
                    "next_action": "Approve or reject",
                }
            )

    return {
        "success": True,
        "data": {
            "campaigns": campaign_list,
            "citations": citation_list,
            "approvals": approval_list,
            "total_active": len(campaign_list) + len(citation_list) + len(approval_list),
        },
        "error": None,
    }
