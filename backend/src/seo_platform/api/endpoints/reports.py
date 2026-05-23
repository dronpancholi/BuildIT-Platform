"""
SEO Platform — Reporting API (Synchronous)
=============================================
Generates real reports from database data without Temporal dependency.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.models.backlink import (
    AcquiredLink,
    BacklinkCampaign,
    BacklinkProspect,
    OutreachThread,
    ThreadStatus,
)
from seo_platform.models.seo import Keyword, KeywordCluster, ReportModel
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()


class ReportMetrics(BaseModel):
    total_campaigns: int = 0
    active_campaigns: int = 0
    draft_campaigns: int = 0
    total_prospects: int = 0
    total_emails_sent: int = 0
    total_replies: int = 0
    total_follow_ups: int = 0
    links_acquired: int = 0
    target_links: int = 0
    acquisition_rate: float = 0.0
    reply_rate: float = 0.0
    avg_health_score: float = 0.0
    total_keywords: int = 0
    total_clusters: int = 0


class CampaignReport(BaseModel):
    id: str
    name: str
    status: str
    campaign_type: str
    target_link_count: int
    acquired_link_count: int
    health_score: float
    total_prospects: int
    emails_sent: int
    replies: int
    follow_ups: int
    created_at: str | None = None


class ProspectReport(BaseModel):
    domain: str
    domain_authority: float
    relevance_score: float
    composite_score: float
    status: str
    contact_email: str | None = None


class EmailReport(BaseModel):
    prospect_domain: str
    subject: str
    status: str
    sent_at: str | None = None
    replied_at: str | None = None
    follow_up_count: int = 0


class FullReportResponse(BaseModel):
    id: str
    report_type: str
    generated_at: str
    tenant_id: str
    client_id: str | None = None
    metrics: ReportMetrics
    campaigns: list[CampaignReport]
    prospects: list[ProspectReport]
    emails: list[EmailReport]
    acquired_links: list[dict]
    keywords: list[dict]
    executive_summary: str


class GenerateReportRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID | None = None
    campaign_id: UUID | None = None
    report_type: str = Field(default="performance", pattern="^(performance|backlink|keyword|full)$")


@router.post("/generate", response_model=APIResponse[FullReportResponse])
async def generate_report_sync(request: GenerateReportRequest) -> APIResponse[FullReportResponse]:
    """Generate a complete report synchronously from real database data."""
    from uuid import uuid4

    async with get_tenant_session(request.tenant_id) as session:
        campaign_filter = [BacklinkCampaign.tenant_id == request.tenant_id]
        if request.client_id:
            campaign_filter.append(BacklinkCampaign.client_id == request.client_id)
        if request.campaign_id:
            campaign_filter.append(BacklinkCampaign.id == request.campaign_id)

        campaigns_result = await session.execute(
            select(BacklinkCampaign).where(*campaign_filter).order_by(BacklinkCampaign.created_at.desc())
        )
        campaigns = campaigns_result.scalars().all()

        campaign_ids = [c.id for c in campaigns]

        prospects_result = await session.execute(
            select(BacklinkProspect).where(
                BacklinkProspect.tenant_id == request.tenant_id,
                BacklinkProspect.campaign_id.in_(campaign_ids) if campaign_ids else False,
            ).order_by(BacklinkProspect.composite_score.desc())
        )
        prospects = prospects_result.scalars().all()

        threads_result = await session.execute(
            select(OutreachThread).where(
                OutreachThread.tenant_id == request.tenant_id,
                OutreachThread.campaign_id.in_(campaign_ids) if campaign_ids else False,
            ).order_by(OutreachThread.created_at.desc())
        )
        threads = threads_result.scalars().all()

        links_result = await session.execute(
            select(AcquiredLink).where(
                AcquiredLink.tenant_id == request.tenant_id,
                AcquiredLink.campaign_id.in_(campaign_ids) if campaign_ids else False,
            ).order_by(AcquiredLink.created_at.desc())
        )
        acquired_links = links_result.scalars().all()

        keywords_result = await session.execute(
            select(Keyword).where(
                Keyword.tenant_id == request.tenant_id,
            ).order_by(Keyword.created_at.desc()).limit(50)
        )
        keywords = keywords_result.scalars().all()

        clusters_result = await session.execute(
            select(func.count()).select_from(KeywordCluster).where(
                KeywordCluster.tenant_id == request.tenant_id,
            )
        )
        total_clusters = clusters_result.scalar_one() or 0

        total_prospects = len(prospects)
        total_emails_sent = sum(1 for t in threads if t.status in (ThreadStatus.SENT, ThreadStatus.DELIVERED, ThreadStatus.OPENED, ThreadStatus.REPLIED, ThreadStatus.LINK_ACQUIRED))
        total_replies = sum(1 for t in threads if t.status == ThreadStatus.REPLIED)
        total_follow_ups = sum(t.follow_up_count for t in threads)
        links_acquired = len(acquired_links)
        target_links = sum(c.target_link_count for c in campaigns)
        active_campaigns = sum(1 for c in campaigns if c.status.value in ("active", "monitoring"))
        draft_campaigns = sum(1 for c in campaigns if c.status.value == "draft")
        avg_health = sum(c.health_score for c in campaigns) / len(campaigns) if campaigns else 0
        outreach_complete = total_emails_sent + total_replies + links_acquired
        reply_rate = total_replies / max(outreach_complete, 1)
        acquisition_rate = links_acquired / max(target_links, 1) if target_links > 0 else 0

        metrics = ReportMetrics(
            total_campaigns=len(campaigns),
            active_campaigns=active_campaigns,
            draft_campaigns=draft_campaigns,
            total_prospects=total_prospects,
            total_emails_sent=total_emails_sent,
            total_replies=total_replies,
            total_follow_ups=total_follow_ups,
            links_acquired=links_acquired,
            target_links=target_links,
            acquisition_rate=round(acquisition_rate, 4),
            reply_rate=round(reply_rate, 4),
            avg_health_score=round(avg_health, 4),
            total_keywords=len(keywords),
            total_clusters=total_clusters,
        )

        campaign_reports = [
            CampaignReport(
                id=str(c.id),
                name=c.name,
                status=c.status.value,
                campaign_type=c.campaign_type.value,
                target_link_count=c.target_link_count,
                acquired_link_count=c.acquired_link_count,
                health_score=round(c.health_score, 4),
                total_prospects=c.total_prospects,
                emails_sent=c.total_emails_sent,
                replies=0,
                follow_ups=0,
                created_at=c.created_at.isoformat() if c.created_at else None,
            )
            for c in campaigns
        ]

        prospect_reports = [
            ProspectReport(
                domain=p.domain,
                domain_authority=p.domain_authority,
                relevance_score=p.relevance_score,
                composite_score=p.composite_score,
                status=p.status.value,
                contact_email=p.contact_email,
            )
            for p in prospects[:50]
        ]

        email_reports = [
            EmailReport(
                prospect_domain=t.prospect.domain if t.prospect else "unknown",
                subject=t.subject,
                status=t.status.value if hasattr(t.status, "value") else str(t.status),
                sent_at=t.sent_at.isoformat() if t.sent_at else None,
                replied_at=t.replied_at.isoformat() if t.replied_at else None,
                follow_up_count=t.follow_up_count,
            )
            for t in threads[:50]
        ]

        link_reports = [
            {
                "source_url": al.source_url,
                "target_url": al.target_url,
                "anchor_text": al.anchor_text,
                "link_type": al.link_type,
                "status": al.status.value,
                "domain_authority": al.domain_authority_at_acquisition,
                "verified_at": al.first_verified_at.isoformat() if al.first_verified_at else None,
            }
            for al in acquired_links
        ]

        keyword_reports = [
            {
                "keyword": k.keyword,
                "search_volume": k.search_volume,
                "difficulty": k.difficulty,
                "cpc": k.cpc,
                "competition": k.competition,
                "intent": k.intent.value if k.intent else "unknown",
            }
            for k in keywords[:50]
        ]

        if links_acquired > 0:
            summary = (
                f"Generated report for {len(campaigns)} campaign(s). "
                f"{total_prospects} prospects identified, {total_emails_sent} emails sent, "
                f"{total_replies} replies received, {links_acquired} links acquired. "
                f"Acquisition rate: {acquisition_rate * 100:.1f}%, Reply rate: {reply_rate * 100:.1f}%. "
                f"Average campaign health: {avg_health * 100:.0f}%."
            )
        elif total_emails_sent > 0:
            summary = (
                f"Generated report for {len(campaigns)} campaign(s). "
                f"{total_prospects} prospects identified, {total_emails_sent} emails sent. "
                f"Awaiting replies and link acquisitions. "
                f"Average campaign health: {avg_health * 100:.0f}%."
            )
        else:
            summary = (
                f"Generated report for {len(campaigns)} campaign(s). "
                f"{total_prospects} prospects identified. "
                f"No emails sent yet. Launch campaigns to begin outreach."
            )

        report = FullReportResponse(
            id=str(uuid4()),
            report_type=request.report_type,
            generated_at=datetime.now(UTC).isoformat(),
            tenant_id=str(request.tenant_id),
            client_id=str(request.client_id) if request.client_id else None,
            metrics=metrics,
            campaigns=campaign_reports,
            prospects=prospect_reports,
            emails=email_reports,
            acquired_links=link_reports,
            keywords=keyword_reports,
            executive_summary=summary,
        )

        report_model = ReportModel(
            id=UUID(report.id),
            tenant_id=request.tenant_id,
            client_id=request.client_id,
            report_type=request.report_type,
            metrics=metrics.model_dump(),
            ai_summary={"executive_summary": summary},
            generated_at=datetime.now(UTC),
        )
        session.add(report_model)
        await session.flush()

        return APIResponse(data=report)


@router.get("", response_model=APIResponse[list[dict]])
async def list_reports(
    tenant_id: UUID = Query(...),
    client_id: UUID | None = None,
) -> APIResponse[list[dict]]:
    """List generated reports for a tenant/client."""
    reports = []
    try:
        async with get_tenant_session(tenant_id) as session:
            query = select(ReportModel).where(ReportModel.tenant_id == tenant_id)
            if client_id:
                query = query.where(ReportModel.client_id == client_id)
            query = query.order_by(ReportModel.generated_at.desc())
            result = await session.execute(query)
            for row in result.scalars().all():
                reports.append({
                    "id": str(row.id),
                    "report_type": row.report_type,
                    "status": "completed",
                    "generated_at": row.generated_at.isoformat() if row.generated_at else "",
                    "client_id": str(row.client_id) if row.client_id else None,
                })
    except Exception as e:
        logger.warning("report_list_failed", error=str(e))

    return APIResponse(data=reports)


@router.get("/{report_id}", response_model=APIResponse[FullReportResponse])
async def get_report(
    report_id: str,
    tenant_id: UUID = Query(...),
) -> APIResponse[FullReportResponse]:
    """Retrieve a specific report by ID."""
    async with get_tenant_session(tenant_id) as session:
        report = await session.get(ReportModel, UUID(report_id))
        if not report or report.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Report not found")

        return APIResponse(
            data=FullReportResponse(
                id=str(report.id),
                report_type=report.report_type,
                generated_at=report.generated_at.isoformat() if report.generated_at else "",
                tenant_id=str(report.tenant_id),
                client_id=str(report.client_id) if report.client_id else None,
                metrics=ReportMetrics(**(report.metrics or {})),
                campaigns=[],
                prospects=[],
                emails=[],
                acquired_links=[],
                keywords=[],
                executive_summary=(report.ai_summary or {}).get("executive_summary", "Report available."),
            )
        )
