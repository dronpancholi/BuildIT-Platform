"""
SEO Platform — Action Center V2
================================
Unified "What needs attention right now?" view for operators.
Aggregates overdue tasks, high-priority tasks, campaign health alerts,
citation failures, outreach follow-ups, pending approvals, and recommendations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_, or_

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.models.approval import ApprovalRequestModel, ApprovalStatusEnum
from seo_platform.models.backlink import BacklinkCampaign, OutreachThread, ThreadStatus
from seo_platform.models.business_memory import CampaignHealthSnapshot, RecommendationModel
from seo_platform.models.citation_v2 import CitationSubmissionV2
from seo_platform.models.seo_task import SEOTask, TaskStatus, TaskPriority
from seo_platform.models.tenant import Client
from seo_platform.schemas import APIResponse, ResponseMeta

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class AttentionItem(BaseModel):
    id: str
    type: str  # task | campaign_alert | citation_failure | outreach_followup | approval | recommendation
    priority: str  # P0 | P1 | P2 | P3
    title: str
    description: str | None = None
    client_id: str | None = None
    client_name: str | None = None
    campaign_id: str | None = None
    campaign_name: str | None = None
    source: str
    impact_score: int | None = None
    due_date: str | None = None
    actions_available: list[str] = Field(default_factory=list)
    entity_type: str | None = None
    entity_id: str | None = None
    created_at: str | None = None


class ActionCenterSummary(BaseModel):
    total_items: int
    by_type: dict[str, int]
    by_priority: dict[str, int]
    oldest_item_days: int
    newest_item_hours: int


class QuickStats(BaseModel):
    open_tasks: int
    overdue_tasks: int
    active_campaigns: int
    pending_approvals: int
    failed_citations: int
    outreach_needing_action: int


class ActionCenterResponse(BaseModel):
    attention_items: list[AttentionItem]
    summary: ActionCenterSummary
    quick_stats: QuickStats


class IgnoreRequest(BaseModel):
    item_id: str
    item_type: str


class SnoozeRequest(BaseModel):
    item_id: str
    item_type: str
    snooze_until: datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _priority_from_task(task: SEOTask) -> str:
    p = task.priority.value if isinstance(task.priority, TaskPriority) else task.priority
    return p if p in ("P0", "P1", "P2", "P3") else "P2"


def _priority_from_health(score: float) -> str:
    if score < 0.2:
        return "P0"
    if score < 0.4:
        return "P1"
    if score < 0.6:
        return "P2"
    return "P3"


def _days_ago(dt: datetime | None) -> int:
    if not dt:
        return 0
    delta = datetime.now(UTC) - dt
    return max(0, delta.days)


def _hours_ago(dt: datetime | None) -> int:
    if not dt:
        return 0
    delta = datetime.now(UTC) - dt
    return max(0, int(delta.total_seconds() // 3600))


def _compute_summary(items: list[AttentionItem], now: datetime) -> ActionCenterSummary:
    by_type: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    oldest_days = 0
    newest_hours = 999999

    for item in items:
        by_type[item.type] = by_type.get(item.type, 0) + 1
        by_priority[item.priority] = by_priority.get(item.priority, 0) + 1

        if item.created_at:
            try:
                created = datetime.fromisoformat(item.created_at.replace("Z", "+00:00"))
                days = _days_ago(created)
                hours = _hours_ago(created)
                oldest_days = max(oldest_days, days)
                newest_hours = min(newest_hours, hours)
            except (ValueError, TypeError):
                pass

    if newest_hours == 999999:
        newest_hours = 0

    return ActionCenterSummary(
        total_items=len(items),
        by_type=by_type,
        by_priority=by_priority,
        oldest_item_days=oldest_days,
        newest_item_hours=newest_hours,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/action-center/dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_model=APIResponse[ActionCenterResponse])
async def action_center_dashboard(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ActionCenterResponse]:
    """Unified view of everything needing operator attention."""
    tenant_id = user.tenant_id
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)

    attention_items: list[AttentionItem] = []

    async with get_tenant_session(tenant_id) as session:
        # ------------------------------------------------------------------
        # 1. Overdue tasks
        # ------------------------------------------------------------------
        overdue_result = await session.execute(
            select(SEOTask).where(
                SEOTask.tenant_id == tenant_id,
                SEOTask.due_date < now,
                SEOTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
            ).order_by(SEOTask.due_date.asc())
        )
        overdue_tasks = overdue_result.scalars().all()

        for task in overdue_tasks:
            priority = _priority_from_task(task)
            if priority in ("P2", "P3"):
                priority = "P1"
            attention_items.append(AttentionItem(
                id=str(task.id),
                type="task",
                priority=priority,
                title=task.title,
                description=task.description,
                client_id=str(task.client_id) if task.client_id else None,
                campaign_id=str(task.campaign_id) if task.campaign_id else None,
                source="overdue_task",
                impact_score=task.impact_score,
                due_date=task.due_date.isoformat() if task.due_date else None,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="seo_task",
                entity_id=str(task.id),
                created_at=task.created_at.isoformat() if task.created_at else None,
            ))

        # ------------------------------------------------------------------
        # 2. High-priority tasks (P0/P1, not completed)
        # ------------------------------------------------------------------
        high_priority_result = await session.execute(
            select(SEOTask).where(
                SEOTask.tenant_id == tenant_id,
                SEOTask.priority.in_([TaskPriority.P0, TaskPriority.P1]),
                SEOTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
            ).order_by(
                SEOTask.priority.asc(),
                SEOTask.created_at.asc(),
            )
        )
        high_priority_tasks = high_priority_result.scalars().all()

        seen_task_ids = {item.id for item in attention_items}
        for task in high_priority_tasks:
            if str(task.id) in seen_task_ids:
                continue
            attention_items.append(AttentionItem(
                id=str(task.id),
                type="task",
                priority=_priority_from_task(task),
                title=task.title,
                description=task.description,
                client_id=str(task.client_id) if task.client_id else None,
                campaign_id=str(task.campaign_id) if task.campaign_id else None,
                source="high_priority_task",
                impact_score=task.impact_score,
                due_date=task.due_date.isoformat() if task.due_date else None,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="seo_task",
                entity_id=str(task.id),
                created_at=task.created_at.isoformat() if task.created_at else None,
            ))

        # ------------------------------------------------------------------
        # 3. Campaign health alerts (health_score < 0.5)
        # ------------------------------------------------------------------
        campaign_health_result = await session.execute(
            select(BacklinkCampaign, Client.name)
            .outerjoin(Client, BacklinkCampaign.client_id == Client.id)
            .where(
                BacklinkCampaign.tenant_id == tenant_id,
                BacklinkCampaign.health_score < 0.5,
                BacklinkCampaign.status.notin_(["complete", "cancelled", "archived"]),
            )
        )
        campaign_health_rows = campaign_health_result.all()

        for campaign, client_name in campaign_health_rows:
            attention_items.append(AttentionItem(
                id=str(campaign.id),
                type="campaign_alert",
                priority=_priority_from_health(campaign.health_score),
                title=f"Campaign health critical: {campaign.name}",
                description=f"Health score {campaign.health_score:.0%} — below 50% threshold",
                client_id=str(campaign.client_id) if campaign.client_id else None,
                client_name=client_name,
                campaign_id=str(campaign.id),
                campaign_name=campaign.name,
                source="campaign_health",
                impact_score=int(campaign.health_score * 100),
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="backlink_campaign",
                entity_id=str(campaign.id),
                created_at=campaign.created_at.isoformat() if campaign.created_at else None,
            ))

        # ------------------------------------------------------------------
        # 4. Citation failures
        # ------------------------------------------------------------------
        citation_fail_result = await session.execute(
            select(CitationSubmissionV2).where(
                CitationSubmissionV2.tenant_id == tenant_id,
                CitationSubmissionV2.status == "failed",
            )
        )
        citation_failures = citation_fail_result.scalars().all()

        for sub in citation_failures:
            attention_items.append(AttentionItem(
                id=str(sub.id),
                type="citation_failure",
                priority="P1",
                title=f"Citation submission failed — site {sub.site_id}",
                description=sub.status_notes or "Submission failed with no notes",
                campaign_id=str(sub.project_id) if sub.project_id else None,
                source="citation_failure",
                impact_score=60,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="citation_submission",
                entity_id=str(sub.id),
                created_at=sub.created_at.isoformat() if sub.created_at else None,
            ))

        # ------------------------------------------------------------------
        # 5. Outreach needing follow-up (>7 days sent, no reply)
        # ------------------------------------------------------------------
        outreach_result = await session.execute(
            select(OutreachThread).where(
                OutreachThread.tenant_id == tenant_id,
                OutreachThread.status == ThreadStatus.SENT,
                OutreachThread.sent_at < seven_days_ago,
                OutreachThread.replied_at.is_(None),
            ).order_by(OutreachThread.sent_at.asc())
        )
        outreach_threads = outreach_result.scalars().all()

        for thread in outreach_threads:
            days_since = _days_ago(thread.sent_at)
            attention_items.append(AttentionItem(
                id=str(thread.id),
                type="outreach_followup",
                priority="P2" if days_since < 14 else "P1",
                title=f"No reply from {thread.to_email} — {days_since}d ago",
                description=f"Outreach sent {days_since} days ago with no response",
                campaign_id=str(thread.campaign_id) if thread.campaign_id else None,
                source="outreach_followup",
                impact_score=40,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="outreach_thread",
                entity_id=str(thread.id),
                created_at=thread.created_at.isoformat() if thread.created_at else None,
            ))

        # ------------------------------------------------------------------
        # 6. Pending approvals
        # ------------------------------------------------------------------
        approval_result = await session.execute(
            select(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
            ).order_by(ApprovalRequestModel.created_at.asc())
        )
        pending_approvals = approval_result.scalars().all()

        for approval in pending_approvals:
            risk_priority = {
                "critical": "P0",
                "high": "P1",
                "medium": "P2",
                "low": "P3",
            }.get(
                approval.risk_level.value if hasattr(approval.risk_level, "value") else str(approval.risk_level),
                "P2",
            )
            attention_items.append(AttentionItem(
                id=str(approval.id),
                type="approval",
                priority=risk_priority,
                title=f"Approval needed: {approval.category.value}",
                description=approval.summary,
                source="approval",
                impact_score=80 if risk_priority == "P0" else 60 if risk_priority == "P1" else 40,
                actions_available=["approve", "reject", "snooze"],
                entity_type="approval_request",
                entity_id=str(approval.id),
                created_at=approval.created_at.isoformat() if approval.created_at else None,
            ))

        # ------------------------------------------------------------------
        # 7. Recommendations not yet turned into tasks
        # ------------------------------------------------------------------
        rec_result = await session.execute(
            select(RecommendationModel).where(
                RecommendationModel.tenant_id == tenant_id,
                RecommendationModel.status == "active",
                RecommendationModel.entity_type.notin_(["seo_task"]),
            ).order_by(RecommendationModel.impact_score.desc())
        )
        recommendations = rec_result.scalars().all()

        for rec in recommendations[:20]:
            impact = int(rec.impact_score) if rec.impact_score else 50
            attention_items.append(AttentionItem(
                id=str(rec.id),
                type="recommendation",
                priority=rec.priority if rec.priority in ("P0", "P1", "P2", "P3") else "P2",
                title=rec.title,
                description=rec.description,
                source="recommendation",
                impact_score=impact,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="recommendation",
                entity_id=str(rec.id),
                created_at=rec.created_at.isoformat() if rec.created_at else None,
            ))

        # ------------------------------------------------------------------
        # Resolve client + campaign names for items missing them
        # ------------------------------------------------------------------
        client_ids = {
            uuid.UUID(item.client_id)
            for item in attention_items
            if item.client_id and not item.client_name
        }
        campaign_ids = {
            uuid.UUID(item.campaign_id)
            for item in attention_items
            if item.campaign_id and not item.campaign_name
        }

        client_map: dict[str, str] = {}
        campaign_map: dict[str, str] = {}

        if client_ids:
            client_result = await session.execute(
                select(Client).where(
                    Client.id.in_(client_ids),
                    Client.tenant_id == tenant_id,
                )
            )
            for c in client_result.scalars().all():
                client_map[str(c.id)] = c.name

        if campaign_ids:
            camp_result = await session.execute(
                select(BacklinkCampaign).where(
                    BacklinkCampaign.id.in_(campaign_ids),
                    BacklinkCampaign.tenant_id == tenant_id,
                )
            )
            for c in camp_result.scalars().all():
                campaign_map[str(c.id)] = c.name

        for item in attention_items:
            if item.client_id and not item.client_name:
                item.client_name = client_map.get(item.client_id)
            if item.campaign_id and not item.campaign_name:
                item.campaign_name = campaign_map.get(item.campaign_id)

        # ------------------------------------------------------------------
        # Sort by priority (P0 first), then impact_score descending
        # ------------------------------------------------------------------
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        attention_items.sort(
            key=lambda x: (priority_order.get(x.priority, 9), -(x.impact_score or 0)),
        )

        # ------------------------------------------------------------------
        # Quick stats
        # ------------------------------------------------------------------
        open_tasks_result = await session.execute(
            select(func.count()).select_from(SEOTask).where(
                SEOTask.tenant_id == tenant_id,
                SEOTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
            )
        )
        open_tasks = open_tasks_result.scalar_one()

        overdue_count_result = await session.execute(
            select(func.count()).select_from(SEOTask).where(
                SEOTask.tenant_id == tenant_id,
                SEOTask.due_date < now,
                SEOTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
            )
        )
        overdue_count = overdue_count_result.scalar_one()

        active_campaigns_result = await session.execute(
            select(func.count()).select_from(BacklinkCampaign).where(
                BacklinkCampaign.tenant_id == tenant_id,
                BacklinkCampaign.status.notin_(["complete", "cancelled", "archived"]),
            )
        )
        active_campaigns = active_campaigns_result.scalar_one()

        pending_approvals_result = await session.execute(
            select(func.count()).select_from(ApprovalRequestModel).where(
                ApprovalRequestModel.tenant_id == tenant_id,
                ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
            )
        )
        pending_approvals_count = pending_approvals_result.scalar_one()

        failed_citations_result = await session.execute(
            select(func.count()).select_from(CitationSubmissionV2).where(
                CitationSubmissionV2.tenant_id == tenant_id,
                CitationSubmissionV2.status == "failed",
            )
        )
        failed_citations_count = failed_citations_result.scalar_one()

        outreach_action_result = await session.execute(
            select(func.count()).select_from(OutreachThread).where(
                OutreachThread.tenant_id == tenant_id,
                OutreachThread.status == ThreadStatus.SENT,
                OutreachThread.sent_at < seven_days_ago,
                OutreachThread.replied_at.is_(None),
            )
        )
        outreach_needing_action = outreach_action_result.scalar_one()

        summary = _compute_summary(attention_items, now)

        quick_stats = QuickStats(
            open_tasks=open_tasks,
            overdue_tasks=overdue_count,
            active_campaigns=active_campaigns,
            pending_approvals=pending_approvals_count,
            failed_citations=failed_citations_count,
            outreach_needing_action=outreach_needing_action,
        )

        return APIResponse(
            data=ActionCenterResponse(
                attention_items=attention_items,
                summary=summary,
                quick_stats=quick_stats,
            ),
            meta=ResponseMeta(total=summary.total_items),
        )


# ---------------------------------------------------------------------------
# GET /api/v1/action-center/prioritized
# ---------------------------------------------------------------------------
@router.get("/prioritized", response_model=APIResponse[list[AttentionItem]])
async def prioritized_items(
    client_id: uuid.UUID | None = Query(default=None),
    type: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[AttentionItem]]:
    """Prioritized attention items sorted by impact (highest first), with optional filters."""
    tenant_id = user.tenant_id
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)

    attention_items: list[AttentionItem] = []

    async with get_tenant_session(tenant_id) as session:
        # Overdue tasks
        overdue_q = select(SEOTask).where(
            SEOTask.tenant_id == tenant_id,
            SEOTask.due_date < now,
            SEOTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
        )
        if client_id:
            overdue_q = overdue_q.where(SEOTask.client_id == client_id)
        overdue_result = await session.execute(overdue_q)
        for task in overdue_result.scalars().all():
            p = _priority_from_task(task)
            if p in ("P2", "P3"):
                p = "P1"
            attention_items.append(AttentionItem(
                id=str(task.id), type="task", priority=p,
                title=task.title, description=task.description,
                client_id=str(task.client_id) if task.client_id else None,
                campaign_id=str(task.campaign_id) if task.campaign_id else None,
                source="overdue_task", impact_score=task.impact_score,
                due_date=task.due_date.isoformat() if task.due_date else None,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="seo_task", entity_id=str(task.id),
                created_at=task.created_at.isoformat() if task.created_at else None,
            ))

        # High-priority tasks
        hp_q = select(SEOTask).where(
            SEOTask.tenant_id == tenant_id,
            SEOTask.priority.in_([TaskPriority.P0, TaskPriority.P1]),
            SEOTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
        )
        if client_id:
            hp_q = hp_q.where(SEOTask.client_id == client_id)
        seen_ids = {item.id for item in attention_items}
        hp_result = await session.execute(hp_q)
        for task in hp_result.scalars().all():
            if str(task.id) not in seen_ids:
                attention_items.append(AttentionItem(
                    id=str(task.id), type="task", priority=_priority_from_task(task),
                    title=task.title, description=task.description,
                    client_id=str(task.client_id) if task.client_id else None,
                    campaign_id=str(task.campaign_id) if task.campaign_id else None,
                    source="high_priority_task", impact_score=task.impact_score,
                    due_date=task.due_date.isoformat() if task.due_date else None,
                    actions_available=["create_task", "ignore", "snooze"],
                    entity_type="seo_task", entity_id=str(task.id),
                    created_at=task.created_at.isoformat() if task.created_at else None,
                ))

        # Campaign health alerts
        ch_q = select(BacklinkCampaign, Client.name).outerjoin(
            Client, BacklinkCampaign.client_id == Client.id
        ).where(
            BacklinkCampaign.tenant_id == tenant_id,
            BacklinkCampaign.health_score < 0.5,
            BacklinkCampaign.status.notin_(["complete", "cancelled", "archived"]),
        )
        if client_id:
            ch_q = ch_q.where(BacklinkCampaign.client_id == client_id)
        ch_result = await session.execute(ch_q)
        for campaign, client_name in ch_result.all():
            attention_items.append(AttentionItem(
                id=str(campaign.id), type="campaign_alert",
                priority=_priority_from_health(campaign.health_score),
                title=f"Campaign health critical: {campaign.name}",
                description=f"Health score {campaign.health_score:.0%}",
                client_id=str(campaign.client_id) if campaign.client_id else None,
                client_name=client_name,
                campaign_id=str(campaign.id), campaign_name=campaign.name,
                source="campaign_health", impact_score=int(campaign.health_score * 100),
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="backlink_campaign", entity_id=str(campaign.id),
                created_at=campaign.created_at.isoformat() if campaign.created_at else None,
            ))

        # Citation failures
        cf_q = select(CitationSubmissionV2).where(
            CitationSubmissionV2.tenant_id == tenant_id,
            CitationSubmissionV2.status == "failed",
        )
        cf_result = await session.execute(cf_q)
        for sub in cf_result.scalars().all():
            attention_items.append(AttentionItem(
                id=str(sub.id), type="citation_failure", priority="P1",
                title=f"Citation submission failed — site {sub.site_id}",
                description=sub.status_notes or "Submission failed",
                campaign_id=str(sub.project_id) if sub.project_id else None,
                source="citation_failure", impact_score=60,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="citation_submission", entity_id=str(sub.id),
                created_at=sub.created_at.isoformat() if sub.created_at else None,
            ))

        # Outreach follow-ups
        ot_q = select(OutreachThread).where(
            OutreachThread.tenant_id == tenant_id,
            OutreachThread.status == ThreadStatus.SENT,
            OutreachThread.sent_at < seven_days_ago,
            OutreachThread.replied_at.is_(None),
        )
        ot_result = await session.execute(ot_q)
        for thread in ot_result.scalars().all():
            days = _days_ago(thread.sent_at)
            attention_items.append(AttentionItem(
                id=str(thread.id), type="outreach_followup",
                priority="P2" if days < 14 else "P1",
                title=f"No reply from {thread.to_email} — {days}d ago",
                description=f"Sent {days} days ago, no response",
                campaign_id=str(thread.campaign_id) if thread.campaign_id else None,
                source="outreach_followup", impact_score=40,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="outreach_thread", entity_id=str(thread.id),
                created_at=thread.created_at.isoformat() if thread.created_at else None,
            ))

        # Pending approvals
        app_q = select(ApprovalRequestModel).where(
            ApprovalRequestModel.tenant_id == tenant_id,
            ApprovalRequestModel.status == ApprovalStatusEnum.PENDING,
        )
        app_result = await session.execute(app_q)
        for approval in app_result.scalars().all():
            rp = {"critical": "P0", "high": "P1", "medium": "P2", "low": "P3"}.get(
                approval.risk_level.value if hasattr(approval.risk_level, "value") else str(approval.risk_level),
                "P2",
            )
            attention_items.append(AttentionItem(
                id=str(approval.id), type="approval", priority=rp,
                title=f"Approval needed: {approval.category.value}",
                description=approval.summary, source="approval",
                impact_score=80 if rp == "P0" else 60 if rp == "P1" else 40,
                actions_available=["approve", "reject", "snooze"],
                entity_type="approval_request", entity_id=str(approval.id),
                created_at=approval.created_at.isoformat() if approval.created_at else None,
            ))

        # Recommendations
        rec_q = select(RecommendationModel).where(
            RecommendationModel.tenant_id == tenant_id,
            RecommendationModel.status == "active",
            RecommendationModel.entity_type.notin_(["seo_task"]),
        ).order_by(RecommendationModel.impact_score.desc())
        rec_result = await session.execute(rec_q)
        for rec in rec_result.scalars().all()[:20]:
            attention_items.append(AttentionItem(
                id=str(rec.id), type="recommendation",
                priority=rec.priority if rec.priority in ("P0", "P1", "P2", "P3") else "P2",
                title=rec.title, description=rec.description,
                source="recommendation",
                impact_score=int(rec.impact_score) if rec.impact_score else 50,
                actions_available=["create_task", "ignore", "snooze"],
                entity_type="recommendation", entity_id=str(rec.id),
                created_at=rec.created_at.isoformat() if rec.created_at else None,
            ))

    # Apply type filter
    if type:
        attention_items = [i for i in attention_items if i.type == type]

    # Apply priority filter
    if priority:
        attention_items = [i for i in attention_items if i.priority == priority]

    # Sort by impact descending
    attention_items.sort(key=lambda x: -(x.impact_score or 0))

    # Apply limit
    attention_items = attention_items[:limit]

    return APIResponse(
        data=attention_items,
        meta=ResponseMeta(total=len(attention_items)),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/action-center/ignore
# ---------------------------------------------------------------------------
@router.post("/ignore", response_model=APIResponse[dict])
async def ignore_item(
    request: IgnoreRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Marks an attention item as ignored (stored in metadata)."""
    tenant_id = user.tenant_id
    now = datetime.now(UTC)

    async with get_tenant_session(tenant_id) as session:
        if request.item_type == "task":
            result = await session.execute(
                select(SEOTask).where(
                    SEOTask.id == request.item_id,
                    SEOTask.tenant_id == tenant_id,
                )
            )
            task = result.scalar_one_or_none()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            extra = task.extra_data or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["ignored"] = True
            extra["action_center"]["ignored_at"] = now.isoformat()
            extra["action_center"]["ignored_by"] = str(user.id)
            task.extra_data = extra
            task.updated_at = now
            await session.flush()

        elif request.item_type == "campaign_alert":
            result = await session.execute(
                select(BacklinkCampaign).where(
                    BacklinkCampaign.id == request.item_id,
                    BacklinkCampaign.tenant_id == tenant_id,
                )
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
            extra = campaign.config or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["ignored"] = True
            extra["action_center"]["ignored_at"] = now.isoformat()
            extra["action_center"]["ignored_by"] = str(user.id)
            campaign.config = extra
            campaign.updated_at = now
            await session.flush()

        elif request.item_type == "citation_failure":
            result = await session.execute(
                select(CitationSubmissionV2).where(
                    CitationSubmissionV2.id == request.item_id,
                    CitationSubmissionV2.tenant_id == tenant_id,
                )
            )
            sub = result.scalar_one_or_none()
            if not sub:
                raise HTTPException(status_code=404, detail="Citation submission not found")
            extra = sub.form_data or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["ignored"] = True
            extra["action_center"]["ignored_at"] = now.isoformat()
            extra["action_center"]["ignored_by"] = str(user.id)
            sub.form_data = extra
            sub.updated_at = now
            await session.flush()

        elif request.item_type == "outreach_followup":
            result = await session.execute(
                select(OutreachThread).where(
                    OutreachThread.id == request.item_id,
                    OutreachThread.tenant_id == tenant_id,
                )
            )
            thread = result.scalar_one_or_none()
            if not thread:
                raise HTTPException(status_code=404, detail="Outreach thread not found")
            extra = thread.ai_personalization or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["ignored"] = True
            extra["action_center"]["ignored_at"] = now.isoformat()
            extra["action_center"]["ignored_by"] = str(user.id)
            thread.ai_personalization = extra
            thread.updated_at = now
            await session.flush()

        elif request.item_type == "approval":
            result = await session.execute(
                select(ApprovalRequestModel).where(
                    ApprovalRequestModel.id == request.item_id,
                    ApprovalRequestModel.tenant_id == tenant_id,
                )
            )
            approval = result.scalar_one_or_none()
            if not approval:
                raise HTTPException(status_code=404, detail="Approval request not found")
            extra = approval.context_snapshot or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["ignored"] = True
            extra["action_center"]["ignored_at"] = now.isoformat()
            extra["action_center"]["ignored_by"] = str(user.id)
            approval.context_snapshot = extra
            approval.updated_at = now
            await session.flush()

        elif request.item_type == "recommendation":
            result = await session.execute(
                select(RecommendationModel).where(
                    RecommendationModel.id == request.item_id,
                    RecommendationModel.tenant_id == tenant_id,
                )
            )
            rec = result.scalar_one_or_none()
            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation not found")
            rec.status = "dismissed"
            rec.dismissed_at = now
            rec.updated_at = now
            await session.flush()

        else:
            raise HTTPException(status_code=400, detail=f"Unknown item_type: {request.item_type}")

        logger.info(
            "action_center_item_ignored",
            tenant_id=str(tenant_id),
            item_id=request.item_id,
            item_type=request.item_type,
            user_id=str(user.id),
        )

        return APIResponse(data={"ignored": True, "item_id": request.item_id})


# ---------------------------------------------------------------------------
# POST /api/v1/action-center/snooze
# ---------------------------------------------------------------------------
@router.post("/snooze", response_model=APIResponse[dict])
async def snooze_item(
    request: SnoozeRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Snoozes an attention item until the specified date."""
    tenant_id = user.tenant_id
    now = datetime.now(UTC)

    async with get_tenant_session(tenant_id) as session:
        if request.item_type == "task":
            result = await session.execute(
                select(SEOTask).where(
                    SEOTask.id == request.item_id,
                    SEOTask.tenant_id == tenant_id,
                )
            )
            task = result.scalar_one_or_none()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            extra = task.extra_data or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["snoozed_until"] = request.snooze_until.isoformat()
            extra["action_center"]["snoozed_by"] = str(user.id)
            extra["action_center"]["snoozed_at"] = now.isoformat()
            task.extra_data = extra
            task.updated_at = now
            await session.flush()

        elif request.item_type == "campaign_alert":
            result = await session.execute(
                select(BacklinkCampaign).where(
                    BacklinkCampaign.id == request.item_id,
                    BacklinkCampaign.tenant_id == tenant_id,
                )
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
            extra = campaign.config or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["snoozed_until"] = request.snooze_until.isoformat()
            extra["action_center"]["snoozed_by"] = str(user.id)
            extra["action_center"]["snoozed_at"] = now.isoformat()
            campaign.config = extra
            campaign.updated_at = now
            await session.flush()

        elif request.item_type == "citation_failure":
            result = await session.execute(
                select(CitationSubmissionV2).where(
                    CitationSubmissionV2.id == request.item_id,
                    CitationSubmissionV2.tenant_id == tenant_id,
                )
            )
            sub = result.scalar_one_or_none()
            if not sub:
                raise HTTPException(status_code=404, detail="Citation submission not found")
            extra = sub.form_data or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["snoozed_until"] = request.snooze_until.isoformat()
            extra["action_center"]["snoozed_by"] = str(user.id)
            extra["action_center"]["snoozed_at"] = now.isoformat()
            sub.form_data = extra
            sub.updated_at = now
            await session.flush()

        elif request.item_type == "outreach_followup":
            result = await session.execute(
                select(OutreachThread).where(
                    OutreachThread.id == request.item_id,
                    OutreachThread.tenant_id == tenant_id,
                )
            )
            thread = result.scalar_one_or_none()
            if not thread:
                raise HTTPException(status_code=404, detail="Outreach thread not found")
            extra = thread.ai_personalization or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["snoozed_until"] = request.snooze_until.isoformat()
            extra["action_center"]["snoozed_by"] = str(user.id)
            extra["action_center"]["snoozed_at"] = now.isoformat()
            thread.ai_personalization = extra
            thread.updated_at = now
            await session.flush()

        elif request.item_type == "approval":
            result = await session.execute(
                select(ApprovalRequestModel).where(
                    ApprovalRequestModel.id == request.item_id,
                    ApprovalRequestModel.tenant_id == tenant_id,
                )
            )
            approval = result.scalar_one_or_none()
            if not approval:
                raise HTTPException(status_code=404, detail="Approval request not found")
            extra = approval.context_snapshot or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["snoozed_until"] = request.snooze_until.isoformat()
            extra["action_center"]["snoozed_by"] = str(user.id)
            extra["action_center"]["snoozed_at"] = now.isoformat()
            approval.context_snapshot = extra
            approval.updated_at = now
            await session.flush()

        elif request.item_type == "recommendation":
            result = await session.execute(
                select(RecommendationModel).where(
                    RecommendationModel.id == request.item_id,
                    RecommendationModel.tenant_id == tenant_id,
                )
            )
            rec = result.scalar_one_or_none()
            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation not found")
            extra = rec.supporting_data or {}
            extra["action_center"] = extra.get("action_center", {})
            extra["action_center"]["snoozed_until"] = request.snooze_until.isoformat()
            extra["action_center"]["snoozed_by"] = str(user.id)
            extra["action_center"]["snoozed_at"] = now.isoformat()
            rec.supporting_data = extra
            rec.updated_at = now
            await session.flush()

        else:
            raise HTTPException(status_code=400, detail=f"Unknown item_type: {request.item_type}")

        logger.info(
            "action_center_item_snoozed",
            tenant_id=str(tenant_id),
            item_id=request.item_id,
            item_type=request.item_type,
            snooze_until=request.snooze_until.isoformat(),
            user_id=str(user.id),
        )

        return APIResponse(data={
            "snoozed": True,
            "item_id": request.item_id,
            "snooze_until": request.snooze_until.isoformat(),
        })
