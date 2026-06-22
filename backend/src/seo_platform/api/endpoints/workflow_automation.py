"""
SEO Platform — Workflow Automation Engine
==========================================
Scans data sources, creates tasks for issues found, manages automation rules,
and provides audit trail of automated actions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.models.backlink import (
    BacklinkCampaign,
    OutreachThread,
    ThreadStatus,
    CampaignStatus,
)
from seo_platform.models.business_profile import BusinessProfile
from seo_platform.models.citation_v2 import CitationSubmissionV2
from seo_platform.models.seo_task import (
    SEOTask,
    TaskStatus,
    TaskPriority,
    TaskSource,
)
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Automation Rules (hardcoded definitions)
# ---------------------------------------------------------------------------
AUTOMATION_RULES = [
    {
        "id": "campaign_health_alert",
        "name": "Campaign Health Alert",
        "description": "Create task when campaign health drops below 50%",
        "source": "campaign_health",
        "threshold": 0.5,
        "enabled": True,
    },
    {
        "id": "citation_failure_retry",
        "name": "Citation Failure Retry",
        "description": "Create task for failed citation submissions",
        "source": "citation_failure",
        "enabled": True,
    },
    {
        "id": "outreach_followup_reminder",
        "name": "Outreach Follow-up Reminder",
        "description": "Create task when outreach has no reply after 7 days",
        "source": "outreach_followup",
        "days_threshold": 7,
        "enabled": True,
    },
    {
        "id": "stale_campaign_alert",
        "name": "Stale Campaign Alert",
        "description": "Create task when campaign hasn't been updated in 14 days",
        "source": "stale_campaign",
        "days_threshold": 14,
        "enabled": True,
    },
    {
        "id": "incomplete_profile",
        "name": "Incomplete Business Profile",
        "description": "Create task when business profile is missing key fields",
        "source": "incomplete_profile",
        "enabled": True,
    },
]

# In-memory rule state (runtime toggle — resets on restart)
_rule_state: dict[str, bool] = {r["id"]: r["enabled"] for r in AUTOMATION_RULES}

# In-memory audit log (last 200 entries)
_audit_log: list[dict] = []


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AutomationRule(BaseModel):
    id: str
    name: str
    description: str
    source: str
    threshold: float | None = None
    days_threshold: int | None = None
    enabled: bool


class ToggleRuleRequest(BaseModel):
    rule_id: str
    enabled: bool


class ScanResult(BaseModel):
    scanned_at: str
    campaigns_scanned: int = 0
    citations_scanned: int = 0
    outreach_scanned: int = 0
    profiles_scanned: int = 0
    tasks_created: int = 0
    tasks_skipped: int = 0
    tasks_by_category: dict[str, int] = Field(default_factory=dict)


class AuditEntry(BaseModel):
    timestamp: str
    rule_id: str
    action: str
    entity_type: str
    entity_id: str | None = None
    task_created: bool = False
    task_id: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


# ---------------------------------------------------------------------------
# GET /automation-rules — List available automation rules
# ---------------------------------------------------------------------------
@router.get("/automation-rules", response_model=APIResponse[list[AutomationRule]])
async def list_automation_rules(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[AutomationRule]]:
    rules = []
    for r in AUTOMATION_RULES:
        rules.append(AutomationRule(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            source=r["source"],
            threshold=r.get("threshold"),
            days_threshold=r.get("days_threshold"),
            enabled=_rule_state.get(r["id"], r["enabled"]),
        ))
    return APIResponse(data=rules)


# ---------------------------------------------------------------------------
# POST /toggle-rule — Enable/disable an automation rule
# ---------------------------------------------------------------------------
@router.post("/toggle-rule", response_model=APIResponse[AutomationRule])
async def toggle_rule(
    body: ToggleRuleRequest,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[AutomationRule]:
    rule_def = next((r for r in AUTOMATION_RULES if r["id"] == body.rule_id), None)
    if not rule_def:
        raise HTTPException(status_code=404, detail=f"Rule '{body.rule_id}' not found")

    _rule_state[body.rule_id] = body.enabled

    logger.info(
        "automation_rule_toggled",
        rule_id=body.rule_id,
        enabled=body.enabled,
        user=str(user.id),
    )

    return APIResponse(
        data=AutomationRule(
            id=rule_def["id"],
            name=rule_def["name"],
            description=rule_def["description"],
            source=rule_def["source"],
            threshold=rule_def.get("threshold"),
            days_threshold=rule_def.get("days_threshold"),
            enabled=body.enabled,
        )
    )


# ---------------------------------------------------------------------------
# POST /scan-and-create-tasks — Scan all data sources, create tasks for issues
# ---------------------------------------------------------------------------
@router.post("/scan-and-create-tasks", response_model=APIResponse[ScanResult])
async def scan_and_create_tasks(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ScanResult]:
    tenant_id = user.tenant_id
    now = datetime.now(UTC)
    tasks_created = 0
    tasks_skipped = 0
    tasks_by_category: dict[str, int] = {}
    campaigns_scanned = 0
    citations_scanned = 0
    outreach_scanned = 0
    profiles_scanned = 0

    async with get_tenant_session(tenant_id) as session:
        # ── 1. Campaign health < 0.5 ──────────────────────────────
        if _rule_state.get("campaign_health_alert", True):
            campaigns_result = await session.execute(
                select(BacklinkCampaign).where(
                    BacklinkCampaign.tenant_id == tenant_id,
                    BacklinkCampaign.status.notin_([
                        CampaignStatus.CANCELLED,
                        CampaignStatus.ARCHIVED,
                        CampaignStatus.COMPLETE,
                    ]),
                )
            )
            campaigns = campaigns_result.scalars().all()
            campaigns_scanned = len(campaigns)

            for campaign in campaigns:
                if campaign.health_score < 0.5:
                    created, skipped = await _create_task_if_needed(
                        session=session,
                        tenant_id=tenant_id,
                        title=f"Review campaign health: {campaign.name} ({campaign.health_score:.0%})",
                        description=f"Campaign '{campaign.name}' health score is {campaign.health_score:.0%}, below the 50% threshold.",
                        priority=TaskPriority.P1,
                        source=TaskSource.CAMPAIGN_HEALTH,
                        source_entity_type="backlink_campaign",
                        source_entity_id=campaign.id,
                        campaign_id=campaign.id,
                        client_id=campaign.client_id,
                        tags=["campaign_health", "automation"],
                        rule_id="campaign_health_alert",
                        now=now,
                    )
                    tasks_created += created
                    tasks_skipped += skipped
                    tasks_by_category["campaign_health"] = tasks_by_category.get("campaign_health", 0) + created

        # ── 2. Failed citation submissions ─────────────────────────
        if _rule_state.get("citation_failure_retry", True):
            citations_result = await session.execute(
                select(CitationSubmissionV2).where(
                    CitationSubmissionV2.tenant_id == tenant_id,
                    CitationSubmissionV2.status == "failed",
                )
            )
            citations = citations_result.scalars().all()
            citations_scanned = len(citations)

            for citation in citations:
                created, skipped = await _create_task_if_needed(
                    session=session,
                    tenant_id=tenant_id,
                    title=f"Retry failed citation (site {citation.site_id})",
                    description=f"Citation submission to site {citation.site_id} failed. Review and retry.",
                    priority=TaskPriority.P1,
                    source=TaskSource.CITATION_FAILURE,
                    source_entity_type="citation_submission",
                    source_entity_id=citation.id,
                    tags=["citation_failure", "automation"],
                    rule_id="citation_failure_retry",
                    now=now,
                )
                tasks_created += created
                tasks_skipped += skipped
                tasks_by_category["citation_failure"] = tasks_by_category.get("citation_failure", 0) + created

        # ── 3. Outreach sent >7 days, no reply ─────────────────────
        if _rule_state.get("outreach_followup_reminder", True):
            cutoff = now - timedelta(days=7)
            outreach_result = await session.execute(
                select(OutreachThread).where(
                    OutreachThread.tenant_id == tenant_id,
                    OutreachThread.status.in_([
                        ThreadStatus.SENT,
                        ThreadStatus.DELIVERED,
                        ThreadStatus.OPENED,
                    ]),
                    OutreachThread.sent_at.isnot(None),
                    OutreachThread.sent_at < cutoff,
                )
            )
            threads = outreach_result.scalars().all()
            outreach_scanned = len(threads)

            for thread in threads:
                created, skipped = await _create_task_if_needed(
                    session=session,
                    tenant_id=tenant_id,
                    title=f"Follow up outreach to {thread.to_email}",
                    description=f"Outreach thread to {thread.to_email} sent on {thread.sent_at.strftime('%Y-%m-%d') if thread.sent_at else 'unknown'} has no reply after 7 days.",
                    priority=TaskPriority.P2,
                    source=TaskSource.OUTREACH_ACTION,
                    source_entity_type="outreach_thread",
                    source_entity_id=thread.id,
                    campaign_id=thread.campaign_id,
                    tags=["outreach_followup", "automation"],
                    rule_id="outreach_followup_reminder",
                    now=now,
                )
                tasks_created += created
                tasks_skipped += skipped
                tasks_by_category["outreach_followup"] = tasks_by_category.get("outreach_followup", 0) + created

        # ── 4. Incomplete business profiles ────────────────────────
        if _rule_state.get("incomplete_profile", True):
            profiles_result = await session.execute(
                select(BusinessProfile).where(
                    BusinessProfile.tenant_id == tenant_id,
                )
            )
            profiles = profiles_result.scalars().all()
            profiles_scanned = len(profiles)

            _REQUIRED_FIELDS = ["description", "primary_category", "website_url"]
            for profile in profiles:
                missing = [
                    f for f in _REQUIRED_FIELDS
                    if not getattr(profile, f, None)
                ]
                if missing:
                    created, skipped = await _create_task_if_needed(
                        session=session,
                        tenant_id=tenant_id,
                        title=f"Complete business profile: {profile.business_name}",
                        description=f"Business profile is missing fields: {', '.join(missing)}",
                        priority=TaskPriority.P2,
                        source=TaskSource.MANUAL,
                        source_entity_type="business_profile",
                        source_entity_id=profile.id,
                        client_id=profile.client_id,
                        tags=["incomplete_profile", "automation"],
                        rule_id="incomplete_profile",
                        now=now,
                    )
                    tasks_created += created
                    tasks_skipped += skipped
                    tasks_by_category["incomplete_profile"] = tasks_by_category.get("incomplete_profile", 0) + created

    # ── Build audit entry ──────────────────────────────────────
    _audit_log.insert(0, {
        "timestamp": now.isoformat(),
        "rule_id": "scan_and_create_tasks",
        "action": "scan",
        "entity_type": "system",
        "entity_id": None,
        "task_created": tasks_created > 0,
        "task_id": None,
        "skipped": False,
        "skip_reason": None,
        "summary": {
            "campaigns_scanned": campaigns_scanned,
            "citations_scanned": citations_scanned,
            "outreach_scanned": outreach_scanned,
            "profiles_scanned": profiles_scanned,
            "tasks_created": tasks_created,
            "tasks_skipped": tasks_skipped,
        },
    })
    # Trim to 200 entries
    if len(_audit_log) > 200:
        _audit_log[:] = _audit_log[:200]

    logger.info(
        "scan_and_create_tasks_completed",
        tenant_id=str(tenant_id),
        tasks_created=tasks_created,
        tasks_skipped=tasks_skipped,
    )

    return APIResponse(
        data=ScanResult(
            scanned_at=now.isoformat(),
            campaigns_scanned=campaigns_scanned,
            citations_scanned=citations_scanned,
            outreach_scanned=outreach_scanned,
            profiles_scanned=profiles_scanned,
            tasks_created=tasks_created,
            tasks_skipped=tasks_skipped,
            tasks_by_category=tasks_by_category,
        )
    )


# ---------------------------------------------------------------------------
# GET /audit — Recent automated task creation audit log
# ---------------------------------------------------------------------------
@router.get("/audit", response_model=APIResponse[list[AuditEntry]])
async def get_audit_log(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[AuditEntry]]:
    entries = [
        AuditEntry(
            timestamp=e.get("timestamp", ""),
            rule_id=e.get("rule_id", ""),
            action=e.get("action", ""),
            entity_type=e.get("entity_type", ""),
            entity_id=e.get("entity_id"),
            task_created=e.get("task_created", False),
            task_id=e.get("task_id"),
            skipped=e.get("skipped", False),
            skip_reason=e.get("skip_reason"),
        )
        for e in _audit_log[:100]
    ]
    return APIResponse(data=entries)


# ---------------------------------------------------------------------------
# Internal: Idempotent task creation
# ---------------------------------------------------------------------------
async def _create_task_if_needed(
    *,
    session,
    tenant_id: UUID,
    title: str,
    description: str,
    priority: TaskPriority,
    source: TaskSource,
    source_entity_type: str,
    source_entity_id: UUID,
    client_id: UUID | None = None,
    campaign_id: UUID | None = None,
    tags: list[str],
    rule_id: str,
    now: datetime,
) -> tuple[int, int]:
    """
    Create a task only if one doesn't already exist for this entity + rule.
    Returns (created, skipped) counts.
    """
    # Check for existing task with same entity + source (idempotency)
    existing = await session.execute(
        select(func.count()).select_from(SEOTask).where(
            SEOTask.tenant_id == tenant_id,
            SEOTask.source_entity_type == source_entity_type,
            SEOTask.source_entity_id == source_entity_id,
            SEOTask.source == source,
            SEOTask.status.notin_([
                TaskStatus.COMPLETED,
                TaskStatus.CANCELLED,
            ]),
        )
    )
    if existing.scalar_one() > 0:
        _audit_log.insert(0, {
            "timestamp": now.isoformat(),
            "rule_id": rule_id,
            "action": "skip",
            "entity_type": source_entity_type,
            "entity_id": str(source_entity_id),
            "task_created": False,
            "task_id": None,
            "skipped": True,
            "skip_reason": "Existing open task found for this entity",
        })
        return 0, 1

    task = SEOTask(
        tenant_id=tenant_id,
        title=title,
        description=description,
        status=TaskStatus.CREATED,
        priority=priority,
        source=source,
        client_id=client_id,
        campaign_id=campaign_id,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        tags=tags,
        extra_data={"rule_id": rule_id, "automated": True},
    )
    session.add(task)
    await session.flush()
    await session.refresh(task)

    _audit_log.insert(0, {
        "timestamp": now.isoformat(),
        "rule_id": rule_id,
        "action": "create",
        "entity_type": source_entity_type,
        "entity_id": str(source_entity_id),
        "task_created": True,
        "task_id": str(task.id),
        "skipped": False,
        "skip_reason": None,
    })

    return 1, 0
