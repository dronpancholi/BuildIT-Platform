"""
SEO Platform — Campaign Operations Engine
==========================================
Single-page unified view of everything happening with a campaign.
Operators see campaign info, objectives, health, tasks, outreach,
citations, timeline, recommendations, and next actions.
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
from seo_platform.models.business_memory import (
    CampaignHealthSnapshot,
    RecommendationModel,
)
from seo_platform.models.citation_v2 import CitationProject, CitationSubmissionV2
from seo_platform.models.observability import CampaignTimelineEvent
from seo_platform.models.seo_task import SEOTask, TaskStatus
from seo_platform.models.tenant import Client
from seo_platform.schemas import APIResponse, ResponseMeta

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class CampaignInfo(BaseModel):
    id: str
    name: str
    status: str
    type: str
    client_name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CampaignObjectives(BaseModel):
    target_links: int
    acquired_links: int
    progress_pct: float
    days_active: int
    velocity: str


class HealthComponent(BaseModel):
    outreach: float = 0.0
    freshness: float = 0.0
    keywords: float = 0.0
    operations: float = 0.0


class CampaignHealth(BaseModel):
    score: float
    tier: str
    momentum: float
    velocity: float
    components: HealthComponent


class TaskSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    overdue: int
    recent: list[dict[str, Any]]


class OutreachSummary(BaseModel):
    threads: int
    by_status: dict[str, int]
    response_rate: float
    needs_followup: int


class CitationsSummary(BaseModel):
    total_submissions: int
    by_status: dict[str, int]


class TimelineEvent(BaseModel):
    id: str
    step_name: str
    status: str
    message: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    priority: str
    impact_score: float


class CampaignOperationsDashboard(BaseModel):
    campaign: CampaignInfo
    objectives: CampaignObjectives
    health: CampaignHealth
    tasks: TaskSummary
    outreach: OutreachSummary
    citations: CitationsSummary
    timeline: list[TimelineEvent]
    recommendations: list[RecommendationItem]
    next_actions: list[str]


class CampaignOverviewItem(BaseModel):
    id: str
    name: str
    status: str
    type: str
    client_name: str | None = None
    health_score: float
    acquired_links: int
    target_links: int
    last_activity: str | None = None


class CampaignOverview(BaseModel):
    total: int
    by_status: dict[str, int]
    needs_attention: list[CampaignOverviewItem]
    campaigns: list[CampaignOverviewItem]
    recent_activity: list[TimelineEvent]


class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = "P1"
    assigned_to: str | None = None
    due_date: datetime | None = None


class CreateTaskResponse(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    created_at: str


# ---------------------------------------------------------------------------
# Helper: health tier from score
# ---------------------------------------------------------------------------
def _health_tier(score: float) -> str:
    if score >= 0.85:
        return "EXCELLENT"
    elif score >= 0.70:
        return "GOOD"
    elif score >= 0.50:
        return "FAIR"
    elif score >= 0.30:
        return "POOR"
    return "CRITICAL"


# ---------------------------------------------------------------------------
# GET /api/v1/campaign-operations/{campaign_id}/dashboard
# ---------------------------------------------------------------------------
@router.get("/{campaign_id}/dashboard", response_model=APIResponse[CampaignOperationsDashboard])
async def get_campaign_dashboard(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
) -> APIResponse[CampaignOperationsDashboard]:
    """Unified single-page campaign operations view."""
    from datetime import timezone

    from sqlalchemy.orm import joinedload

    async with get_tenant_session(tenant_id) as session:
        # 1. Campaign info
        result = await session.execute(
            select(BacklinkCampaign)
            .where(
                BacklinkCampaign.id == campaign_id,
                BacklinkCampaign.tenant_id == tenant_id,
            )
            .options(joinedload(BacklinkCampaign.client))
        )
        campaign = result.unique().scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        client_name = campaign.client.name if campaign.client else None
        now = datetime.now(UTC)
        days_active = (now - campaign.created_at).days if campaign.created_at else 0

        # 2. Objectives
        acquired = campaign.acquired_link_count
        target = campaign.target_link_count
        progress_pct = round((acquired / target) * 100, 1) if target > 0 else 0.0
        velocity_val = round(acquired / max(days_active, 1), 2)
        velocity_str = f"{velocity_val} links/day"

        # 3. Health from latest snapshot
        health_result = await session.execute(
            select(CampaignHealthSnapshot)
            .where(CampaignHealthSnapshot.campaign_id == campaign_id)
            .order_by(CampaignHealthSnapshot.captured_at.desc())
            .limit(1)
        )
        health_snap = health_result.scalar_one_or_none()

        if health_snap:
            snap_data = health_snap.snapshot_data or {}
            components = snap_data.get("components", {})
            health = CampaignHealth(
                score=health_snap.health_score,
                tier=_health_tier(health_snap.health_score),
                momentum=health_snap.momentum,
                velocity=health_snap.velocity,
                components=HealthComponent(
                    outreach=components.get("outreach", 0.0),
                    freshness=components.get("freshness", 0.0),
                    keywords=components.get("keywords", 0.0),
                    operations=components.get("operations", 0.0),
                ),
            )
        else:
            health = CampaignHealth(
                score=campaign.health_score or 0.0,
                tier=_health_tier(campaign.health_score or 0.0),
                momentum=0.0,
                velocity=0.0,
                components=HealthComponent(),
            )

        # 4. Tasks
        tasks_result = await session.execute(
            select(SEOTask)
            .where(SEOTask.campaign_id == campaign_id, SEOTask.tenant_id == tenant_id)
            .order_by(SEOTask.created_at.desc())
        )
        tasks = tasks_result.scalars().all()

        task_status_counts: dict[str, int] = {}
        for t in tasks:
            s = t.status.value if hasattr(t.status, "value") else str(t.status)
            task_status_counts[s] = task_status_counts.get(s, 0) + 1

        overdue_tasks = sum(
            1 for t in tasks
            if t.due_date and t.due_date < now
            and (t.status.value if hasattr(t.status, "value") else str(t.status))
            not in ("completed", "cancelled")
        )

        recent_tasks = [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                "priority": t.priority.value if hasattr(t.priority, "value") else str(t.priority),
                "assigned_to": t.assigned_to,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks[:10]
        ]

        # 5. Outreach
        threads_result = await session.execute(
            select(OutreachThread)
            .where(
                OutreachThread.campaign_id == campaign_id,
                OutreachThread.tenant_id == tenant_id,
            )
        )
        threads = threads_result.scalars().all()

        thread_status_counts: dict[str, int] = {}
        for th in threads:
            s = th.status.value if hasattr(th.status, "value") else str(th.status)
            thread_status_counts[s] = thread_status_counts.get(s, 0) + 1

        total_sent = sum(
            1 for th in threads
            if (th.status.value if hasattr(th.status, "value") else str(th.status))
            in ("sent", "delivered", "opened", "replied", "link_acquired")
        )
        total_replied = sum(
            1 for th in threads
            if (th.status.value if hasattr(th.status, "value") else str(th.status))
            in ("replied", "link_acquired")
        )
        response_rate = round(total_replied / max(total_sent, 1), 2)

        # Follow-up detection: sent 7+ days ago, no reply, under max follow-ups
        needs_followup = 0
        for th in threads:
            s = th.status.value if hasattr(th.status, "value") else str(th.status)
            if s in ("sent", "delivered", "opened") and th.sent_at:
                days_since = (now - th.sent_at).days
                if days_since >= 7 and th.follow_up_count < th.max_follow_ups:
                    needs_followup += 1

        # 6. Citations — linked via client_id
        citations: list[Any] = []
        citation_status_counts: dict[str, int] = {}
        if campaign.client_id:
            cit_project_result = await session.execute(
                select(CitationProject.id)
                .where(
                    CitationProject.client_id == campaign.client_id,
                    CitationProject.tenant_id == tenant_id,
                )
            )
            project_ids = [r[0] for r in cit_project_result.all()]
            if project_ids:
                citations_result = await session.execute(
                    select(CitationSubmissionV2)
                    .where(
                        CitationSubmissionV2.project_id.in_(project_ids),
                        CitationSubmissionV2.tenant_id == tenant_id,
                    )
                )
                citations = list(citations_result.scalars().all())
                for c in citations:
                    s = c.status if isinstance(c.status, str) else str(c.status)
                    citation_status_counts[s] = citation_status_counts.get(s, 0) + 1

        # 7. Timeline (last 20 events)
        timeline_result = await session.execute(
            select(CampaignTimelineEvent)
            .where(
                CampaignTimelineEvent.campaign_id == campaign_id,
                CampaignTimelineEvent.tenant_id == tenant_id,
            )
            .order_by(CampaignTimelineEvent.timestamp.desc())
            .limit(20)
        )
        timeline_events = timeline_result.scalars().all()

        timeline = [
            TimelineEvent(
                id=str(e.id),
                step_name=e.step_name,
                status=e.status,
                message=e.message,
                timestamp=e.timestamp.isoformat() if e.timestamp else "",
                metadata=e.step_metadata or {},
            )
            for e in timeline_events
        ]

        # 8. Recommendations linked to this campaign
        recs_result = await session.execute(
            select(RecommendationModel)
            .where(
                RecommendationModel.entity_id == campaign_id,
                RecommendationModel.status == "active",
            )
            .order_by(RecommendationModel.impact_score.desc())
            .limit(10)
        )
        recs = recs_result.scalars().all()

        recommendations = [
            RecommendationItem(
                id=str(r.id),
                type=r.recommendation_type,
                title=r.title,
                description=r.description,
                priority=r.priority,
                impact_score=r.impact_score,
            )
            for r in recs
        ]

        # 9. Next actions — computed from actual data state
        next_actions = _compute_next_actions(
            threads=threads,
            tasks=tasks,
            campaign=campaign,
            now=now,
        )

        return APIResponse(
            data=CampaignOperationsDashboard(
                campaign=CampaignInfo(
                    id=str(campaign.id),
                    name=campaign.name,
                    status=campaign.status.value if hasattr(campaign.status, "value") else str(campaign.status),
                    type=campaign.campaign_type.value if hasattr(campaign.campaign_type, "value") else str(campaign.campaign_type),
                    client_name=client_name,
                    created_at=campaign.created_at.isoformat() if campaign.created_at else None,
                    updated_at=campaign.updated_at.isoformat() if campaign.updated_at else None,
                ),
                objectives=CampaignObjectives(
                    target_links=target,
                    acquired_links=acquired,
                    progress_pct=progress_pct,
                    days_active=days_active,
                    velocity=velocity_str,
                ),
                health=health,
                tasks=TaskSummary(
                    total=len(tasks),
                    by_status=task_status_counts,
                    overdue=overdue_tasks,
                    recent=recent_tasks,
                ),
                outreach=OutreachSummary(
                    threads=len(threads),
                    by_status=thread_status_counts,
                    response_rate=response_rate,
                    needs_followup=needs_followup,
                ),
                citations=CitationsSummary(
                    total_submissions=len(citations),
                    by_status=citation_status_counts,
                ),
                timeline=timeline,
                recommendations=recommendations,
                next_actions=next_actions,
            )
        )


# ---------------------------------------------------------------------------
# GET /api/v1/campaign-operations/overview
# ---------------------------------------------------------------------------
@router.get("/overview", response_model=APIResponse[CampaignOverview])
async def get_campaign_overview(
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
) -> APIResponse[CampaignOverview]:
    """Overview of ALL campaigns for the tenant."""
    from datetime import timezone

    from sqlalchemy.orm import joinedload

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(BacklinkCampaign)
            .where(BacklinkCampaign.tenant_id == tenant_id)
            .options(joinedload(BacklinkCampaign.client))
            .order_by(BacklinkCampaign.updated_at.desc())
        )
        campaigns = result.unique().scalars().all()

        now = datetime.now(UTC)
        status_counts: dict[str, int] = {}
        needs_attention: list[CampaignOverviewItem] = []
        all_campaigns: list[CampaignOverviewItem] = []

        for c in campaigns:
            s = c.status.value if hasattr(c.status, "value") else str(c.status)
            status_counts[s] = status_counts.get(s, 0) + 1

            client_name = c.client.name if c.client else None

            # Determine if campaign needs attention
            is_stale = False
            if c.updated_at:
                days_since_update = (now - c.updated_at).days
                is_stale = days_since_update > 14 and s in ("active", "outreach_prep")

            is_low_health = (c.health_score or 0.0) < 0.5 and s not in ("draft", "cancelled", "archived")
            is_draft_stuck = s == "draft" and c.created_at and (now - c.created_at).days > 7

            item = CampaignOverviewItem(
                id=str(c.id),
                name=c.name,
                status=s,
                type=c.campaign_type.value if hasattr(c.campaign_type, "value") else str(c.campaign_type),
                client_name=client_name,
                health_score=c.health_score or 0.0,
                acquired_links=c.acquired_link_count,
                target_links=c.target_link_count,
                last_activity=c.updated_at.isoformat() if c.updated_at else None,
            )

            all_campaigns.append(item)
            if is_low_health or is_stale or is_draft_stuck:
                needs_attention.append(item)

        # Recent timeline across all campaigns
        timeline_result = await session.execute(
            select(CampaignTimelineEvent)
            .where(CampaignTimelineEvent.tenant_id == tenant_id)
            .order_by(CampaignTimelineEvent.timestamp.desc())
            .limit(15)
        )
        timeline_events = timeline_result.scalars().all()
        recent_timeline = [
            TimelineEvent(
                id=str(e.id),
                step_name=e.step_name,
                status=e.status,
                message=e.message,
                timestamp=e.timestamp.isoformat() if e.timestamp else "",
                metadata=e.step_metadata or {},
            )
            for e in timeline_events
        ]

        return APIResponse(
            data=CampaignOverview(
                total=len(campaigns),
                by_status=status_counts,
                needs_attention=needs_attention,
                campaigns=all_campaigns,
                recent_activity=recent_timeline,
            )
        )


# ---------------------------------------------------------------------------
# POST /api/v1/campaign-operations/{campaign_id}/create-task
# ---------------------------------------------------------------------------
@router.post(
    "/{campaign_id}/create-task",
    response_model=APIResponse[CreateTaskResponse],
    status_code=201,
)
async def create_campaign_task(
    campaign_id: uuid.UUID,
    request: CreateTaskRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[CreateTaskResponse]:
    """Create a task linked to a specific campaign."""
    from datetime import timezone

    from seo_platform.models.seo_task import TaskPriority, TaskSource

    async with get_tenant_session(tenant_id) as session:
        # Verify campaign exists
        campaign = await session.get(BacklinkCampaign, campaign_id)
        if not campaign or campaign.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Campaign not found")

        task = SEOTask(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            title=request.title,
            description=request.description,
            priority=TaskPriority(request.priority),
            source=TaskSource.MANUAL,
            assigned_to=request.assigned_to,
            due_date=request.due_date,
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)

        return APIResponse(
            data=CreateTaskResponse(
                id=str(task.id),
                title=task.title,
                status=task.status.value,
                priority=task.priority.value,
                created_at=task.created_at.isoformat() if task.created_at else None,
            )
        )


# ---------------------------------------------------------------------------
# Next actions computation
# ---------------------------------------------------------------------------
def _compute_next_actions(
    threads: list[OutreachThread],
    tasks: list[SEOTask],
    campaign: BacklinkCampaign,
    now: datetime,
) -> list[str]:
    """Compute actionable next steps based on current campaign state."""
    actions: list[str] = []

    # Threads needing follow-up
    for th in threads:
        s = th.status.value if hasattr(th.status, "value") else str(th.status)
        if s in ("sent", "delivered", "opened") and th.sent_at:
            days_since = (now - th.sent_at).days
            if days_since >= 7 and th.follow_up_count < th.max_follow_ups:
                domain = th.prospect.domain if th.prospect else "unknown"
                actions.append(
                    f"Follow up with {th.to_email} at {domain} (sent {days_since} days ago, no reply)"
                )

    # Overdue tasks
    for t in tasks:
        ts = t.status.value if hasattr(t.status, "value") else str(t.status)
        if t.due_date and t.due_date < now and ts not in ("completed", "cancelled"):
            actions.append(f"Complete overdue task: {t.title} (due {t.due_date.strftime('%Y-%m-%d')})")

    # Campaign progress check
    if campaign.acquired_link_count < campaign.target_link_count:
        remaining = campaign.target_link_count - campaign.acquired_link_count
        actions.append(f"{remaining} more links needed to reach target ({campaign.acquired_link_count}/{campaign.target_link_count})")

    # Prospect outreach gap
    if campaign.total_prospects > campaign.total_emails_sent:
        gap = campaign.total_prospects - campaign.total_emails_sent
        actions.append(f"Generate outreach emails for {gap} prospects without emails")

    # Health-based actions
    if campaign.health_score and campaign.health_score < 0.5:
        actions.append("Campaign health is low — review outreach strategy and prospect quality")

    return actions[:10]  # Cap at 10 next actions
