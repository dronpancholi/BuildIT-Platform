"""
SEO Platform — Outreach Operations Engine
==========================================
Centralized operational view of all outreach threads: status tracking,
follow-up management, response rate analytics, and lifecycle transitions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_, or_

from seo_platform.core.auth import CurrentUser, get_validated_tenant_id
from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.rbac import RequirePermission
from seo_platform.models.backlink import (
    AcquiredLink,
    BacklinkCampaign,
    BacklinkProspect,
    OutreachThread,
    ThreadStatus,
)
from seo_platform.models.communication import OutreachEmail, EmailTemplate
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Valid lifecycle transitions
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["queued", "cancelled"],
    "queued": ["sent", "cancelled"],
    "sent": ["opened", "replied", "link_acquired", "failed"],
    "opened": ["replied", "link_acquired", "failed"],
    "replied": ["link_acquired", "failed"],
    "link_acquired": [],
    "failed": [],
    "cancelled": [],
}


def _enum_val(val: Any) -> str:
    return val.value if hasattr(val, "value") else str(val)


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------
class ThreadSummary(BaseModel):
    id: str
    prospect_domain: str | None = None
    to_email: str
    subject: str
    status: str
    follow_up_count: int
    max_follow_ups: int
    sent_at: str | None = None
    replied_at: str | None = None
    days_since_sent: int | None = None
    needs_followup: bool = False
    campaign_id: str
    campaign_name: str | None = None


class OutreachDashboard(BaseModel):
    total_threads: int
    by_status: dict[str, int]
    response_rate: float
    reply_rate: float
    needs_followup_count: int
    needs_followup_threads: list[ThreadSummary]
    recent_activity: list[dict[str, Any]]


class EmailInThread(BaseModel):
    id: str
    direction: str
    to_email: str | None = None
    from_email: str | None = None
    subject: str | None = None
    body_preview: str | None = None
    status: str | None = None
    sent_at: str | None = None


class StatusTimelineEntry(BaseModel):
    status: str
    changed_at: str
    notes: str | None = None


class ThreadDetail(BaseModel):
    id: str
    campaign_id: str
    campaign_name: str | None = None
    prospect_domain: str | None = None
    prospect_url: str | None = None
    to_email: str
    from_email: str
    subject: str
    status: str
    follow_up_count: int
    max_follow_ups: int
    confidence_score: float
    sent_at: str | None = None
    opened_at: str | None = None
    replied_at: str | None = None
    created_at: str | None = None
    emails: list[EmailInThread]
    status_timeline: list[StatusTimelineEntry]
    recommended_next_action: str


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New status value")
    notes: str | None = None


class BulkFollowUpResponse(BaseModel):
    tasks_created: int
    thread_ids: list[str]


class CampaignRate(BaseModel):
    campaign_id: str
    campaign_name: str
    total_sent: int
    total_replied: int
    response_rate: float


class TemplateRate(BaseModel):
    template_id: str
    template_name: str
    usage_count: int
    response_count: int
    response_rate: float


class OutreachAnalytics(BaseModel):
    overall_response_rate: float
    overall_reply_rate: float
    total_sent: int
    total_replied: int
    total_opened: int
    rates_by_campaign: list[CampaignRate]
    rates_by_template: list[TemplateRate]
    best_performing_templates: list[TemplateRate]


# ---------------------------------------------------------------------------
# GET /outreach-operations/dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_model=APIResponse[OutreachDashboard])
async def get_outreach_dashboard(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
) -> APIResponse[OutreachDashboard]:
    """Full outreach operations dashboard with status counts, rates, and follow-up alerts."""
    from sqlalchemy.orm import joinedload

    now = datetime.now(UTC)

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(OutreachThread)
            .where(OutreachThread.tenant_id == tenant_id)
            .options(
                joinedload(OutreachThread.campaign),
                joinedload(OutreachThread.prospect),
            )
        )
        threads = result.unique().scalars().all()

        # Status counts
        by_status: dict[str, int] = {}
        for t in threads:
            s = _enum_val(t.status)
            by_status[s] = by_status.get(s, 0) + 1

        # Response & reply rates (sent threads only)
        sent_statuses = {"sent", "delivered", "opened", "replied", "link_acquired"}
        replied_statuses = {"replied", "link_acquired"}
        opened_statuses = {"opened", "replied", "link_acquired"}

        total_sent = sum(1 for t in threads if _enum_val(t.status) in sent_statuses)
        total_replied = sum(1 for t in threads if _enum_val(t.status) in replied_statuses)
        total_opened = sum(1 for t in threads if _enum_val(t.status) in opened_statuses)

        response_rate = round(total_replied / max(total_sent, 1), 4)
        reply_rate = round(total_replied / max(total_sent, 1), 4)

        # Follow-up detection: sent 7+ days ago, no reply, under max follow-ups
        needs_followup_threads: list[ThreadSummary] = []
        for t in threads:
            s = _enum_val(t.status)
            if s in ("sent", "delivered", "opened") and t.sent_at:
                days_since = (now - t.sent_at).days
                if days_since >= 7 and t.follow_up_count < t.max_follow_ups:
                    needs_followup_threads.append(ThreadSummary(
                        id=str(t.id),
                        prospect_domain=t.prospect.domain if t.prospect else None,
                        to_email=t.to_email,
                        subject=t.subject,
                        status=s,
                        follow_up_count=t.follow_up_count,
                        max_follow_ups=t.max_follow_ups,
                        sent_at=t.sent_at.isoformat() if t.sent_at else None,
                        replied_at=t.replied_at.isoformat() if t.replied_at else None,
                        days_since_sent=days_since,
                        needs_followup=True,
                        campaign_id=str(t.campaign_id),
                        campaign_name=t.campaign.name if t.campaign else None,
                    ))

        # Recent activity (last 20 threads by updated_at)
        sorted_threads = sorted(threads, key=lambda t: t.updated_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        recent_activity = [
            {
                "id": str(t.id),
                "to_email": t.to_email,
                "subject": t.subject,
                "status": _enum_val(t.status),
                "campaign_name": t.campaign.name if t.campaign else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in sorted_threads[:20]
        ]

        return APIResponse(
            data=OutreachDashboard(
                total_threads=len(threads),
                by_status=by_status,
                response_rate=response_rate,
                reply_rate=reply_rate,
                needs_followup_count=len(needs_followup_threads),
                needs_followup_threads=needs_followup_threads,
                recent_activity=recent_activity,
            )
        )


# ---------------------------------------------------------------------------
# GET /outreach-operations/thread/{thread_id}
# ---------------------------------------------------------------------------
@router.get("/thread/{thread_id}", response_model=APIResponse[ThreadDetail])
async def get_thread_detail(
    thread_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
) -> APIResponse[ThreadDetail]:
    """Full thread detail including emails, timeline, and recommended next action."""
    from sqlalchemy.orm import joinedload

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(OutreachThread)
            .where(
                OutreachThread.id == thread_id,
                OutreachThread.tenant_id == tenant_id,
            )
            .options(
                joinedload(OutreachThread.campaign),
                joinedload(OutreachThread.prospect),
            )
        )
        thread = result.unique().scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Fetch associated emails from outreach_emails table
        emails_result = await session.execute(
            select(OutreachEmail)
            .where(
                OutreachEmail.campaign_id == thread.campaign_id,
                OutreachEmail.tenant_id == tenant_id,
                OutreachEmail.prospect_id == str(thread.prospect_id),
            )
            .order_by(OutreachEmail.sent_at.asc())
        )
        emails = emails_result.scalars().all()

        email_list = [
            EmailInThread(
                id=str(e.id),
                direction="outbound",
                to_email=e.to_email,
                from_email=None,
                subject=e.subject,
                body_preview=(e.body_html[:200] + "...") if e.body_html and len(e.body_html) > 200 else e.body_html,
                status=_enum_val(e.status) if e.status else None,
                sent_at=e.sent_at.isoformat() if e.sent_at else None,
            )
            for e in emails
        ]

        # Build status timeline from thread fields
        status_timeline: list[StatusTimelineEntry] = []
        if thread.created_at:
            status_timeline.append(StatusTimelineEntry(
                status="draft",
                changed_at=thread.created_at.isoformat(),
            ))
        if thread.sent_at:
            status_timeline.append(StatusTimelineEntry(
                status="sent",
                changed_at=thread.sent_at.isoformat(),
            ))
        if thread.opened_at:
            status_timeline.append(StatusTimelineEntry(
                status="opened",
                changed_at=thread.opened_at.isoformat(),
            ))
        if thread.replied_at:
            status_timeline.append(StatusTimelineEntry(
                status="replied",
                changed_at=thread.replied_at.isoformat(),
            ))

        # Recommended next action
        next_action = _recommend_next_action(thread)

        return APIResponse(
            data=ThreadDetail(
                id=str(thread.id),
                campaign_id=str(thread.campaign_id),
                campaign_name=thread.campaign.name if thread.campaign else None,
                prospect_domain=thread.prospect.domain if thread.prospect else None,
                prospect_url=thread.prospect.url if thread.prospect else None,
                to_email=thread.to_email,
                from_email=thread.from_email,
                subject=thread.subject,
                status=_enum_val(thread.status),
                follow_up_count=thread.follow_up_count,
                max_follow_ups=thread.max_follow_ups,
                confidence_score=thread.confidence_score,
                sent_at=thread.sent_at.isoformat() if thread.sent_at else None,
                opened_at=thread.opened_at.isoformat() if thread.opened_at else None,
                replied_at=thread.replied_at.isoformat() if thread.replied_at else None,
                created_at=thread.created_at.isoformat() if thread.created_at else None,
                emails=email_list,
                status_timeline=status_timeline,
                recommended_next_action=next_action,
            )
        )


def _recommend_next_action(thread: OutreachThread) -> str:
    status = _enum_val(thread.status)
    now = datetime.now(UTC)

    if status == "draft":
        return "Queue this thread for sending."
    if status == "queued":
        return "Thread is queued — will be sent on next dispatch cycle."
    if status in ("sent", "delivered", "opened") and thread.sent_at:
        days_since = (now - thread.sent_at).days
        if days_since >= 7 and thread.follow_up_count < thread.max_follow_ups:
            return f"Send follow-up #{thread.follow_up_count + 1} — no reply after {days_since} days."
        if days_since < 7:
            return f"Waiting — email sent {days_since} day(s) ago. Follow-up eligible after 7 days."
        return "Max follow-ups reached. Consider marking as failed or unresponsive."
    if status == "replied":
        return "Prospect replied! Review the response and proceed with link acquisition."
    if status == "link_acquired":
        return "Link acquired — thread complete. Monitor for link removal."
    if status == "failed":
        return "Thread failed. Review the reason and consider a new outreach attempt."
    if status == "cancelled":
        return "Thread was cancelled."
    return "No action available."


# ---------------------------------------------------------------------------
# POST /outreach-operations/thread/{thread_id}/status
# ---------------------------------------------------------------------------
@router.post(
    "/thread/{thread_id}/status",
    response_model=APIResponse[ThreadSummary],
)
async def update_thread_status(
    thread_id: uuid.UUID,
    request: StatusUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[ThreadSummary]:
    """Change thread status with lifecycle validation."""
    from sqlalchemy.orm import joinedload

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(OutreachThread)
            .where(
                OutreachThread.id == thread_id,
                OutreachThread.tenant_id == tenant_id,
            )
            .options(
                joinedload(OutreachThread.campaign),
                joinedload(OutreachThread.prospect),
            )
        )
        thread = result.unique().scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        current_status = _enum_val(thread.status)
        new_status = request.status

        # Validate transition
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: {current_status} → {new_status}. Allowed: {allowed}",
            )

        now = datetime.now(UTC)

        # Apply transition
        thread.status = ThreadStatus(new_status)

        if new_status == "sent" and not thread.sent_at:
            thread.sent_at = now
        elif new_status == "opened" and not thread.opened_at:
            thread.opened_at = now
        elif new_status == "replied" and not thread.replied_at:
            thread.replied_at = now

        thread.updated_at = now
        await session.flush()
        await session.refresh(thread)

        logger.info(
            "outreach_thread_status_changed",
            thread_id=str(thread_id),
            old_status=current_status,
            new_status=new_status,
            notes=request.notes,
        )

        return APIResponse(
            data=ThreadSummary(
                id=str(thread.id),
                prospect_domain=thread.prospect.domain if thread.prospect else None,
                to_email=thread.to_email,
                subject=thread.subject,
                status=_enum_val(thread.status),
                follow_up_count=thread.follow_up_count,
                max_follow_ups=thread.max_follow_ups,
                sent_at=thread.sent_at.isoformat() if thread.sent_at else None,
                replied_at=thread.replied_at.isoformat() if thread.replied_at else None,
                campaign_id=str(thread.campaign_id),
                campaign_name=thread.campaign.name if thread.campaign else None,
            )
        )


# ---------------------------------------------------------------------------
# POST /outreach-operations/bulk-follow-up
# ---------------------------------------------------------------------------
@router.post(
    "/bulk-follow-up",
    response_model=APIResponse[BulkFollowUpResponse],
)
async def bulk_create_follow_ups(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[BulkFollowUpResponse]:
    """Create follow-up tasks for all threads needing follow-up (sent 7+ days, no reply)."""
    from sqlalchemy.orm import joinedload

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=7)

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(OutreachThread)
            .where(
                OutreachThread.tenant_id == tenant_id,
                OutreachThread.status.in_([
                    ThreadStatus.SENT,
                    ThreadStatus.DELIVERED,
                    ThreadStatus.OPENED,
                ]),
                OutreachThread.sent_at <= cutoff,
                OutreachThread.follow_up_count < OutreachThread.max_follow_ups,
            )
            .options(joinedload(OutreachThread.prospect))
        )
        threads = result.unique().scalars().all()

        thread_ids: list[str] = []
        for t in threads:
            t.follow_up_count += 1
            t.updated_at = now
            thread_ids.append(str(t.id))

        await session.flush()

        logger.info(
            "bulk_follow_up_created",
            count=len(thread_ids),
        )

        return APIResponse(
            data=BulkFollowUpResponse(
                tasks_created=len(thread_ids),
                thread_ids=thread_ids,
            )
        )


# ---------------------------------------------------------------------------
# GET /outreach-operations/analytics
# ---------------------------------------------------------------------------
@router.get("/analytics", response_model=APIResponse[OutreachAnalytics])
async def get_outreach_analytics(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
) -> APIResponse[OutreachAnalytics]:
    """Outreach analytics: response rates by campaign and template."""
    async with get_tenant_session(tenant_id) as session:
        # All threads for this tenant
        result = await session.execute(
            select(OutreachThread).where(OutreachThread.tenant_id == tenant_id)
        )
        threads = result.scalars().all()

        sent_statuses = {"sent", "delivered", "opened", "replied", "link_acquired"}
        replied_statuses = {"replied", "link_acquired"}
        opened_statuses = {"opened", "replied", "link_acquired"}

        total_sent = sum(1 for t in threads if _enum_val(t.status) in sent_statuses)
        total_replied = sum(1 for t in threads if _enum_val(t.status) in replied_statuses)
        total_opened = sum(1 for t in threads if _enum_val(t.status) in opened_statuses)

        overall_response_rate = round(total_replied / max(total_sent, 1), 4)
        overall_reply_rate = round(total_replied / max(total_sent, 1), 4)

        # Rates by campaign
        campaign_threads: dict[str, list[OutreachThread]] = {}
        for t in threads:
            cid = str(t.campaign_id)
            campaign_threads.setdefault(cid, []).append(t)

        # Fetch campaign names
        campaign_result = await session.execute(
            select(BacklinkCampaign).where(BacklinkCampaign.tenant_id == tenant_id)
        )
        campaigns_map = {str(c.id): c for c in campaign_result.scalars().all()}

        rates_by_campaign: list[CampaignRate] = []
        for cid, cthreads in campaign_threads.items():
            c_sent = sum(1 for t in cthreads if _enum_val(t.status) in sent_statuses)
            c_replied = sum(1 for t in cthreads if _enum_val(t.status) in replied_statuses)
            camp = campaigns_map.get(cid)
            rates_by_campaign.append(CampaignRate(
                campaign_id=cid,
                campaign_name=camp.name if camp else "Unknown",
                total_sent=c_sent,
                total_replied=c_replied,
                response_rate=round(c_replied / max(c_sent, 1), 4),
            ))

        # Rates by template (from email_templates table)
        template_result = await session.execute(
            select(EmailTemplate).where(EmailTemplate.tenant_id == tenant_id)
        )
        templates = template_result.scalars().all()

        rates_by_template: list[TemplateRate] = []
        for tmpl in templates:
            # Count emails sent using this template by matching subject patterns
            email_result = await session.execute(
                select(func.count(OutreachEmail.id))
                .where(
                    OutreachEmail.tenant_id == tenant_id,
                    OutreachEmail.subject.ilike(f"%{tmpl.name}%"),
                )
            )
            usage = email_result.scalar() or 0

            # Count replies to emails with this subject pattern
            reply_result = await session.execute(
                select(func.count(OutreachEmail.id))
                .where(
                    OutreachEmail.tenant_id == tenant_id,
                    OutreachEmail.subject.ilike(f"%{tmpl.name}%"),
                    OutreachEmail.status == "replied",
                )
            )
            replies = reply_result.scalar() or 0

            rates_by_template.append(TemplateRate(
                template_id=str(tmpl.id),
                template_name=tmpl.name,
                usage_count=usage,
                response_count=replies,
                response_rate=round(replies / max(usage, 1), 4),
            ))

        # Best performing (sorted by response rate, min 3 uses)
        best_performing = sorted(
            [t for t in rates_by_template if t.usage_count >= 3],
            key=lambda t: t.response_rate,
            reverse=True,
        )[:5]

        return APIResponse(
            data=OutreachAnalytics(
                overall_response_rate=overall_response_rate,
                overall_reply_rate=overall_reply_rate,
                total_sent=total_sent,
                total_replied=total_replied,
                total_opened=total_opened,
                rates_by_campaign=rates_by_campaign,
                rates_by_template=rates_by_template,
                best_performing_templates=best_performing,
            )
        )
