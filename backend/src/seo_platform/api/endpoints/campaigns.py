"""
SEO Platform — Campaign Endpoints
=====================================
Campaign management with workflow triggering.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse, ResponseMeta

router = APIRouter()


class CreateCampaignRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    campaign_type: str = "guest_post"
    competitor_domains: list[str] = Field(default_factory=list)
    target_link_count: int = Field(default=10, ge=1, le=500)
    min_domain_authority: float = Field(default=30.0, ge=0, le=100)
    max_spam_score: float = Field(default=5.0, ge=0, le=100)


class UpdateCampaignRequest(BaseModel):
    name: str | None = None
    campaign_type: str | None = None
    target_link_count: int | None = Field(default=None, ge=1, le=500)
    competitor_domains: list[str] | None = None
    min_domain_authority: float | None = Field(default=None, ge=0, le=100)
    max_spam_score: float | None = Field(default=None, ge=0, le=100)


class CampaignResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID
    name: str
    campaign_type: str
    status: str
    target_link_count: int
    acquired_link_count: int
    health_score: float
    workflow_run_id: str | None
    client_name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CampaignLaunchResponse(BaseModel):
    campaign_id: str
    workflow_run_id: str
    status: str


@router.get("", response_model=APIResponse[list[CampaignResponse]])
async def list_campaigns(
    tenant_id: UUID = Query(...),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> APIResponse[list[CampaignResponse]]:
    """List all backlink campaigns for a tenant."""
    from sqlalchemy import func, select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign

    async with get_tenant_session(tenant_id) as session:
        count_result = await session.execute(
            select(func.count()).select_from(BacklinkCampaign).where(
                BacklinkCampaign.tenant_id == tenant_id
            )
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(BacklinkCampaign)
            .where(BacklinkCampaign.tenant_id == tenant_id)
            .order_by(BacklinkCampaign.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        campaigns = result.scalars().all()

        return APIResponse(
            data=[
                CampaignResponse(
                    id=c.id,
                    tenant_id=c.tenant_id,
                    client_id=c.client_id,
                    name=c.name,
                    campaign_type=c.campaign_type.value,
                    status=c.status.value,
                    target_link_count=c.target_link_count,
                    acquired_link_count=c.acquired_link_count,
                    health_score=c.health_score,
                    workflow_run_id=c.workflow_run_id,
                    created_at=c.created_at.isoformat() if c.created_at else None,
                    updated_at=c.updated_at.isoformat() if c.updated_at else None,
                )
                for c in campaigns
            ],
            meta=ResponseMeta(total=total, offset=offset, limit=limit, has_more=(offset + limit) < total),
        )


@router.post("", response_model=APIResponse[CampaignResponse], status_code=201)
async def create_campaign(request: CreateCampaignRequest) -> APIResponse[CampaignResponse]:
    """Create a new backlink campaign (draft status)."""
    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign, CampaignType

    async with get_tenant_session(request.tenant_id) as session:
        campaign = BacklinkCampaign(
            tenant_id=request.tenant_id,
            client_id=request.client_id,
            name=request.name,
            campaign_type=CampaignType(request.campaign_type),
            target_link_count=request.target_link_count,
            config={
                "competitor_domains": request.competitor_domains,
                "min_domain_authority": request.min_domain_authority,
                "max_spam_score": request.max_spam_score,
            },
        )
        session.add(campaign)
        await session.flush()
        await session.refresh(campaign)

        return APIResponse(
            data=CampaignResponse(
                id=campaign.id,
                tenant_id=campaign.tenant_id,
                client_id=campaign.client_id,
                name=campaign.name,
                campaign_type=campaign.campaign_type.value,
                status=campaign.status.value,
                target_link_count=campaign.target_link_count,
                acquired_link_count=campaign.acquired_link_count,
                health_score=campaign.health_score,
                workflow_run_id=campaign.workflow_run_id,
                created_at=campaign.created_at.isoformat() if campaign.created_at else None,
                updated_at=campaign.updated_at.isoformat() if campaign.updated_at else None,
            )
        )


class ThreadResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    campaign_name: str | None
    prospect_domain: str
    prospect_name: str | None
    to_email: str | None
    subject: str
    body_html: str
    status: str
    follow_up_count: int
    sent_at: str | None
    replied_at: str | None
    created_at: str | None
    updated_at: str | None
    confidence_score: float
    ai_personalization: dict


@router.get("/threads/all", response_model=APIResponse[list[ThreadResponse]])
async def list_all_threads(
    tenant_id: UUID = Query(...),
) -> APIResponse[list[ThreadResponse]]:
    """List all outreach threads across all campaigns for a tenant (Outbox view)."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect, OutreachThread

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(OutreachThread)
            .join(BacklinkProspect, OutreachThread.prospect_id == BacklinkProspect.id)
            .join(BacklinkCampaign, OutreachThread.campaign_id == BacklinkCampaign.id)
            .where(OutreachThread.tenant_id == tenant_id)
            .options(
                joinedload(OutreachThread.prospect),
                joinedload(OutreachThread.campaign),
            )
            .order_by(OutreachThread.sent_at.desc().nulls_last(), OutreachThread.created_at.desc())
        )
        threads = result.unique().scalars().all()

        return APIResponse(
            data=[
                ThreadResponse(
                    id=t.id,
                    campaign_id=t.campaign_id,
                    campaign_name=t.campaign.name if t.campaign else None,
                    prospect_domain=t.prospect.domain if t.prospect else "",
                    prospect_name=t.prospect.contact_name if t.prospect else None,
                    to_email=t.to_email,
                    subject=t.subject or "",
                    body_html=t.body_html or "",
                    status=t.status.value if hasattr(t.status, "value") else str(t.status),
                    follow_up_count=t.follow_up_count,
                    sent_at=t.sent_at.isoformat() if t.sent_at else None,
                    replied_at=t.replied_at.isoformat() if t.replied_at else None,
                    created_at=t.created_at.isoformat() if t.created_at else None,
                    updated_at=t.updated_at.isoformat() if t.updated_at else None,
                    confidence_score=t.confidence_score,
                    ai_personalization=t.ai_personalization or {},
                )
                for t in threads
            ],
        )


@router.get("/{campaign_id}/threads", response_model=APIResponse[list[ThreadResponse]])
async def list_campaign_threads(
    campaign_id: UUID,
    tenant_id: UUID = Query(...),
) -> APIResponse[list[ThreadResponse]]:
    """List outreach threads with composed emails for a campaign."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect, OutreachThread

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(OutreachThread)
            .join(BacklinkProspect, OutreachThread.prospect_id == BacklinkProspect.id)
            .join(BacklinkCampaign, OutreachThread.campaign_id == BacklinkCampaign.id)
            .where(
                OutreachThread.tenant_id == tenant_id,
                OutreachThread.campaign_id == campaign_id,
            )
            .options(
                joinedload(OutreachThread.prospect),
                joinedload(OutreachThread.campaign),
            )
            .order_by(OutreachThread.sent_at.desc().nulls_last(), OutreachThread.created_at.desc())
        )
        threads = result.unique().scalars().all()

        return APIResponse(
            data=[
                ThreadResponse(
                    id=t.id,
                    campaign_id=t.campaign_id,
                    campaign_name=t.campaign.name if t.campaign else None,
                    prospect_domain=t.prospect.domain if t.prospect else "",
                    prospect_name=t.prospect.contact_name if t.prospect else None,
                    to_email=t.to_email,
                    subject=t.subject or "",
                    body_html=t.body_html or "",
                    status=t.status.value if hasattr(t.status, "value") else str(t.status),
                    follow_up_count=t.follow_up_count,
                    sent_at=t.sent_at.isoformat() if t.sent_at else None,
                    replied_at=t.replied_at.isoformat() if t.replied_at else None,
                    created_at=t.created_at.isoformat() if t.created_at else None,
                    updated_at=t.updated_at.isoformat() if t.updated_at else None,
                    confidence_score=t.confidence_score,
                    ai_personalization=t.ai_personalization or {},
                )
                for t in threads
            ],
        )


class UpdateThreadRequest(BaseModel):
    subject: str | None = None
    body_html: str | None = None


class ThreadUpdateResponse(BaseModel):
    id: UUID
    status: str
    updated_at: str


@router.put("/threads/{thread_id}", response_model=APIResponse[ThreadUpdateResponse])
async def update_thread(
    thread_id: UUID,
    request: UpdateThreadRequest,
    tenant_id: UUID = Query(...),
) -> APIResponse[ThreadUpdateResponse]:
    """Update a thread's subject or body (for editing drafts)."""
    from datetime import datetime, timezone

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import OutreachThread

    async with get_tenant_session(tenant_id) as session:
        thread = await session.get(OutreachThread, thread_id)
        if not thread or thread.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Thread not found")

        if request.subject is not None:
            thread.subject = request.subject
        if request.body_html is not None:
            thread.body_html = request.body_html

        thread.updated_at = datetime.now(timezone.utc)
        await session.flush()

        return APIResponse(
            data=ThreadUpdateResponse(
                id=thread.id,
                status=thread.status.value if hasattr(thread.status, "value") else str(thread.status),
                updated_at=thread.updated_at.isoformat() if thread.updated_at else None,
            )
        )


class SendThreadRequest(BaseModel):
    pass


class SendThreadResponse(BaseModel):
    id: UUID
    status: str
    sent_at: str
    provider: str


@router.post("/threads/{thread_id}/send", response_model=APIResponse[SendThreadResponse])
async def send_thread_email(
    thread_id: UUID,
    request: SendThreadRequest,
    tenant_id: UUID = Query(...),
) -> APIResponse[SendThreadResponse]:
    """Send a draft email thread via MailHog SMTP."""
    from datetime import datetime, timezone

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import OutreachThread, ThreadStatus
    from seo_platform.services.email_provider import MailhogProvider

    async with get_tenant_session(tenant_id) as session:
        thread = await session.get(OutreachThread, thread_id)
        if not thread or thread.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.status not in (ThreadStatus.DRAFT, ThreadStatus.QUEUED):
            raise HTTPException(status_code=400, detail=f"Cannot send thread in {thread.status} status")

        provider = MailhogProvider()
        result = await provider.send_email(
            to_email=thread.to_email,
            subject=thread.subject,
            body=thread.body_html,
            campaign_id=str(thread.campaign_id),
            tenant_id=str(tenant_id),
            prospect_id=str(thread.prospect_id),
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=f"Email send failed: {result.get('error')}")

        thread.status = ThreadStatus.SENT
        thread.sent_at = datetime.now(timezone.utc)
        thread.updated_at = datetime.now(timezone.utc)
        await session.flush()

        return APIResponse(
            data=SendThreadResponse(
                id=thread.id,
                status=thread.status.value,
                sent_at=thread.sent_at.isoformat(),
                provider=result.get("provider", "mailhog"),
            )
        )


class SimulateReplyRequest(BaseModel):
    reply_body: str = "Thank you for reaching out. I'd be happy to discuss this further."


class SimulateReplyResponse(BaseModel):
    id: UUID
    status: str
    replied_at: str


@router.post("/threads/{thread_id}/simulate-reply", response_model=APIResponse[SimulateReplyResponse])
async def simulate_thread_reply(
    thread_id: UUID,
    request: SimulateReplyRequest,
    tenant_id: UUID = Query(...),
) -> APIResponse[SimulateReplyResponse]:
    """Simulate a reply to a sent thread for testing purposes."""
    from datetime import datetime, timezone

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import OutreachThread, ThreadStatus

    async with get_tenant_session(tenant_id) as session:
        thread = await session.get(OutreachThread, thread_id)
        if not thread or thread.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.status != ThreadStatus.SENT:
            raise HTTPException(status_code=400, detail=f"Cannot simulate reply to thread in {thread.status} status")

        thread.status = ThreadStatus.REPLIED
        thread.replied_at = datetime.now(timezone.utc)
        thread.updated_at = datetime.now(timezone.utc)
        thread.ai_personalization = {
            **(thread.ai_personalization or {}),
            "reply_body": request.reply_body,
            "reply_simulated": True,
        }
        await session.flush()

        return APIResponse(
            data=SimulateReplyResponse(
                id=thread.id,
                status=thread.status.value,
                replied_at=thread.replied_at.isoformat(),
            )
        )


class ScheduleFollowUpRequest(BaseModel):
    follow_up_body: str
    follow_up_subject: str | None = None


class ScheduleFollowUpResponse(BaseModel):
    id: UUID
    follow_up_count: int
    status: str


@router.post("/threads/{thread_id}/follow-up", response_model=APIResponse[ScheduleFollowUpResponse])
async def schedule_thread_follow_up(
    thread_id: UUID,
    request: ScheduleFollowUpRequest,
    tenant_id: UUID = Query(...),
) -> APIResponse[ScheduleFollowUpResponse]:
    """Schedule and send a follow-up email for a thread."""
    from datetime import datetime, timezone

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import OutreachThread, ThreadStatus
    from seo_platform.services.email_provider import MailhogProvider

    async with get_tenant_session(tenant_id) as session:
        thread = await session.get(OutreachThread, thread_id)
        if not thread or thread.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.status not in (ThreadStatus.SENT, ThreadStatus.REPLIED):
            raise HTTPException(status_code=400, detail=f"Cannot follow up thread in {thread.status} status")

        follow_up_subject = request.follow_up_subject or f"Re: {thread.subject}"
        provider = MailhogProvider()
        result = await provider.send_email(
            to_email=thread.to_email,
            subject=follow_up_subject,
            body=request.follow_up_body,
            campaign_id=str(thread.campaign_id),
            tenant_id=str(tenant_id),
            prospect_id=str(thread.prospect_id),
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=f"Follow-up send failed: {result.get('error')}")

        thread.follow_up_count += 1
        thread.body_html = request.follow_up_body
        thread.subject = follow_up_subject
        thread.updated_at = datetime.now(timezone.utc)
        await session.flush()

        return APIResponse(
            data=ScheduleFollowUpResponse(
                id=thread.id,
                follow_up_count=thread.follow_up_count,
                status=thread.status.value if hasattr(thread.status, "value") else str(thread.status),
            )
        )


class MarkLinkAcquiredRequest(BaseModel):
    acquired_url: str
    anchor_text: str = ""


class MarkLinkAcquiredResponse(BaseModel):
    thread_id: UUID
    prospect_domain: str
    acquired_url: str
    status: str


@router.post("/threads/{thread_id}/mark-link-acquired", response_model=APIResponse[MarkLinkAcquiredResponse])
async def mark_thread_link_acquired(
    thread_id: UUID,
    request: MarkLinkAcquiredRequest,
    tenant_id: UUID = Query(...),
) -> APIResponse[MarkLinkAcquiredResponse]:
    """Mark a thread as having acquired a backlink and update campaign metrics."""
    from datetime import datetime, timezone

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import (
        AcquiredLink,
        BacklinkCampaign,
        BacklinkProspect,
        LinkStatus,
        OutreachThread,
        ThreadStatus,
    )

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(OutreachThread)
            .where(OutreachThread.id == thread_id, OutreachThread.tenant_id == tenant_id)
            .options(selectinload(OutreachThread.prospect))
        )
        thread = result.scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        prospect_domain = thread.prospect.domain if thread.prospect else "unknown"
        prospect_da = thread.prospect.domain_authority if thread.prospect else 0

        thread.status = ThreadStatus.LINK_ACQUIRED
        thread.updated_at = datetime.now(timezone.utc)
        thread.ai_personalization = {
            **(thread.ai_personalization or {}),
            "acquired_url": request.acquired_url,
            "anchor_text": request.anchor_text,
            "link_acquired_at": datetime.now(timezone.utc).isoformat(),
        }

        acquired = AcquiredLink(
            tenant_id=tenant_id,
            campaign_id=thread.campaign_id,
            prospect_id=thread.prospect_id,
            source_url=request.acquired_url,
            target_url=f"https://{prospect_domain}",
            anchor_text=request.anchor_text,
            link_type="dofollow",
            status=LinkStatus.VERIFIED_LIVE,
            domain_authority_at_acquisition=prospect_da,
            first_verified_at=datetime.now(timezone.utc),
        )
        session.add(acquired)

        campaign = await session.get(BacklinkCampaign, thread.campaign_id)
        if campaign:
            campaign.acquired_link_count += 1
            if campaign.target_link_count > 0:
                campaign.acquisition_rate = round(
                    campaign.acquired_link_count / campaign.target_link_count, 4
                )

        await session.flush()

        return APIResponse(
            data=MarkLinkAcquiredResponse(
                thread_id=thread.id,
                prospect_domain=prospect_domain,
                acquired_url=request.acquired_url,
                status=thread.status.value,
            )
        )


@router.get("/{campaign_id}", response_model=APIResponse[CampaignResponse])
async def get_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Query(...),
) -> APIResponse[CampaignResponse]:
    """Get a single campaign by ID."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign

    async with get_tenant_session(tenant_id) as session:
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

        return APIResponse(
            data=CampaignResponse(
                id=campaign.id,
                tenant_id=campaign.tenant_id,
                client_id=campaign.client_id,
                client_name=client_name,
                name=campaign.name,
                campaign_type=campaign.campaign_type.value,
                status=campaign.status.value,
                target_link_count=campaign.target_link_count,
                acquired_link_count=campaign.acquired_link_count,
                health_score=campaign.health_score,
                workflow_run_id=campaign.workflow_run_id,
                created_at=campaign.created_at.isoformat() if campaign.created_at else None,
                updated_at=campaign.updated_at.isoformat() if campaign.updated_at else None,
            )
        )


@router.put("/{campaign_id}", response_model=APIResponse[CampaignResponse])
async def update_campaign(
    campaign_id: UUID,
    request: UpdateCampaignRequest,
    tenant_id: UUID = Query(...),
) -> APIResponse[CampaignResponse]:
    """Update an existing campaign."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign, CampaignType

    async with get_tenant_session(tenant_id) as session:
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

        if request.name is not None:
            campaign.name = request.name
        if request.campaign_type is not None:
            campaign.campaign_type = CampaignType(request.campaign_type)
        if request.target_link_count is not None:
            campaign.target_link_count = request.target_link_count
        if request.competitor_domains is not None:
            config = dict(campaign.config or {})
            config["competitor_domains"] = request.competitor_domains
            campaign.config = config
        if request.min_domain_authority is not None:
            config = dict(campaign.config or {})
            config["min_domain_authority"] = request.min_domain_authority
            campaign.config = config
        if request.max_spam_score is not None:
            config = dict(campaign.config or {})
            config["max_spam_score"] = request.max_spam_score
            campaign.config = config

        await session.flush()
        await session.refresh(campaign)

        client_name = campaign.client.name if campaign.client else None

        return APIResponse(
            data=CampaignResponse(
                id=campaign.id,
                tenant_id=campaign.tenant_id,
                client_id=campaign.client_id,
                client_name=client_name,
                name=campaign.name,
                campaign_type=campaign.campaign_type.value,
                status=campaign.status.value,
                target_link_count=campaign.target_link_count,
                acquired_link_count=campaign.acquired_link_count,
                health_score=campaign.health_score,
                workflow_run_id=campaign.workflow_run_id,
                created_at=campaign.created_at.isoformat() if campaign.created_at else None,
                updated_at=campaign.updated_at.isoformat() if campaign.updated_at else None,
            )
        )


class GenerateEmailRequest(BaseModel):
    tenant_id: UUID


class GenerateEmailResponse(BaseModel):
    prospect_domain: str
    prospect_name: str | None
    subject: str
    body_html: str
    generation_source: str
    compliance_score: float
    compliance_passed: bool


@router.post("/{campaign_id}/generate-emails", response_model=APIResponse[list[GenerateEmailResponse]])
async def generate_campaign_emails(
    campaign_id: UUID,
    request: GenerateEmailRequest,
) -> APIResponse[list[GenerateEmailResponse]]:
    """Generate personalized outreach emails for all prospects in a campaign.
    Uses NVIDIA NIM LLM when API key is configured, falls back to
    elite deterministic template. Each email is saved as an OutreachThread."""
    import json as json_mod
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from seo_platform.config import get_settings
    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import (
        BacklinkCampaign, BacklinkProspect, ProspectStatus,
        OutreachThread, ThreadStatus,
    )
    from seo_platform.services.compliance_scorer import compliance_scorer

    settings = get_settings()
    use_nim = settings.nvidia.api_key and "mock" not in settings.nvidia.api_key.lower()

    async with get_tenant_session(request.tenant_id) as session:
        campaign = await session.get(BacklinkCampaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        prospects = (
            await session.execute(
                select(BacklinkProspect)
                .where(
                    BacklinkProspect.campaign_id == campaign_id,
                    BacklinkProspect.tenant_id == request.tenant_id,
                )
                .options(joinedload(BacklinkProspect.threads))
            )
        ).unique().scalars().all()

        results: list[GenerateEmailResponse] = []
        niche = "enterprise SaaS and DevOps" if "tech" in campaign.name.lower() else "local business"

        for prospect in prospects:
            if prospect.threads:
                continue

            domain = prospect.domain
            name = prospect.contact_name or "there"
            first_name = name.split()[0] if name != "there" else "there"

            subj = f"Quick question regarding your recent thoughts on {niche}"
            body = (
                f"<p>Hi {first_name},</p>"
                f"<p>I really enjoyed your recent piece on {domain.split('.')[0]} "
                f"regarding {niche}. It's rare to see someone address the nuances so directly.</p>"
                f"<p>We recently compiled exclusive benchmark data at {campaign.name} "
                f"exploring this exact space. I thought the custom insights might be a "
                f"perfect drop-in addition for your upcoming coverage.</p>"
                f"<p>Would you be open to me sending over a quick preview link?</p>"
                f"<p>Best regards,<br/>{campaign.name} Team</p>"
            )
            ai_personalization = {"generation_source": "elite_deterministic_fallback"}

            if use_nim:
                try:
                    import httpx
                    model = settings.nvidia.seo_model
                    prompt = (
                        f"You are a senior outreach strategist. Write a short, personalized email "
                        f"to convince {name} at {domain} to agree to a backlink placement for "
                        f"{campaign.name} in the niche '{niche}'. "
                        f"The email must be concise, research-driven, and reference the prospect's work. "
                        f"Respond in JSON with keys 'subject', 'body_html' (HTML with <p> tags), and 'icebreaker'."
                    )
                    async with httpx.AsyncClient(
                        headers={
                            "Authorization": f"Bearer {settings.nvidia.api_key}",
                            "Content-Type": "application/json",
                        },
                        timeout=httpx.Timeout(30),
                    ) as client:
                        resp = await client.post(f"{settings.nvidia.api_url}/chat/completions", json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "You are an elite outreach strategist. Return valid JSON only."},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.7,
                            "max_tokens": 512,
                            "response_format": {"type": "json_object"},
                        })
                        resp.raise_for_status()
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        parsed = json_mod.loads(content)
                        subj = parsed.get("subject", subj)
                        body = parsed.get("body_html", body)
                        ai_personalization = {
                            "icebreaker": parsed.get("icebreaker", ""),
                            "generation_source": "nvidia_nim",
                            "model": model,
                        }
                except Exception as e:
                    from seo_platform.core.logging import get_logger
                    get_logger(__name__).warning("nim_email_generation_failed", error=str(e))

            compliance = await compliance_scorer.score_email_pitch(
                tenant_id=request.tenant_id,
                email_body=body,
                entity_id=prospect.id,
                entity_type="email_pitch",
            )

            thread = OutreachThread(
                tenant_id=request.tenant_id,
                campaign_id=campaign_id,
                prospect_id=prospect.id,
                status=ThreadStatus.DRAFT,
                from_email="demo@buildit.local",
                to_email=prospect.contact_email or f"contact@{domain}",
                subject=subj,
                body_html=body,
                follow_up_count=0,
                max_follow_ups=3,
                provider="nvidia_nim" if use_nim else "demo",
                confidence_score=compliance.get("score", 0.85) or 0.85,
                ai_personalization=ai_personalization,
            )
            session.add(thread)

            results.append(GenerateEmailResponse(
                prospect_domain=domain,
                prospect_name=prospect.contact_name,
                subject=subj,
                body_html=body,
                generation_source=ai_personalization.get("generation_source", "elite_deterministic_fallback"),
                compliance_score=compliance.get("score", 0.0),
                compliance_passed=compliance.get("passed", True),
            ))

        await session.flush()

        return APIResponse(data=results)


class DiscoveryRequest(BaseModel):
    tenant_id: UUID
    max_prospects: int = Field(default=30, ge=1, le=100)


class DiscoveryProspectResponse(BaseModel):
    domain: str
    domain_authority: float
    relevance_score: float
    spam_score: float
    composite_score: float
    source: str


class DiscoveryResponse(BaseModel):
    campaign_id: str
    prospects_discovered: int
    prospects: list[DiscoveryProspectResponse]


@router.post("/{campaign_id}/discover", response_model=APIResponse[DiscoveryResponse])
async def discover_prospects_sync(
    campaign_id: UUID,
    request: DiscoveryRequest,
) -> APIResponse[DiscoveryResponse]:
    """Synchronous backlink prospect discovery fallback when Temporal is unavailable.
    Uses SearXNG to find real domains mentioning competitor domains,
    calculates authority metrics, and persists to Postgres."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import (
        BacklinkCampaign,
        BacklinkProspect,
        ProspectStatus,
    )
    from seo_platform.providers.seo import (
        ScraplingSEOProvider,
        SearXNGSEOProvider,
        calculate_local_authority,
    )

    async with get_tenant_session(request.tenant_id) as session:
        campaign = await session.get(BacklinkCampaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        competitor_domains = campaign.config.get("competitor_domains", [])
        if not competitor_domains:
            raise HTTPException(
                status_code=400,
                detail="Campaign has no competitor_domains configured",
            )

        min_da = campaign.config.get("min_domain_authority", 30.0)
        max_prospects = request.max_prospects
        seen_domains: set[str] = set()
        discovered: list[dict] = []

        providers_to_try = [SearXNGSEOProvider(), ScraplingSEOProvider()]

        for competitor in competitor_domains:
            if len(discovered) >= max_prospects:
                break

            for provider in providers_to_try:
                if len(discovered) >= max_prospects:
                    break

                try:
                    prospects = await provider.discover_backlink_prospects(
                        competitor, limit=max_prospects // len(competitor_domains) + 5
                    )
                    for p in prospects:
                        if len(discovered) >= max_prospects:
                            break
                        dom = p.domain
                        if not dom or dom in seen_domains:
                            continue
                        seen_domains.add(dom)

                        da = calculate_local_authority(dom)
                        relevance = min(1.0, p.relevance_score or 0.7)
                        spam = p.spam_score or 0.02
                        composite = round(
                            (da / 100.0) * 0.45 + relevance * 0.40 + (1.0 - spam) * 0.15, 4
                        )

                        if da < min_da:
                            continue

                        discovered.append({
                            "domain": dom,
                            "url": f"https://{dom}/",
                            "domain_authority": round(da, 1),
                            "relevance_score": relevance,
                            "spam_score": spam,
                            "composite_score": composite,
                            "source": p.source,
                        })
                except Exception as e:
                    from seo_platform.core.logging import get_logger
                    get_logger(__name__).warning(
                        "discovery_provider_failed",
                        provider=provider.name,
                        competitor=competitor,
                        error=str(e),
                    )
                    continue

        import httpx
        from seo_platform.core.logging import get_logger
        log = get_logger(__name__)

        if len(discovered) < max_prospects:
            for competitor in competitor_domains:
                if len(discovered) >= max_prospects:
                    break

                public_sources = [
                    {
                        "url": f"https://api.hackertarget.com/linktracer/?q={competitor}",
                        "parser": "plain_text_domains",
                    },
                    {
                        "url": f"https://api.hackertarget.com/pagelinks/?q={competitor}",
                        "parser": "plain_text_domains",
                    },
                    {
                        "url": f"https://api.hackertarget.com/hostsearch/?q={competitor}",
                        "parser": "plain_text_domains",
                    },
                    {
                        "url": f"https://api.hackertarget.com/findshareddns/?q={competitor}",
                        "parser": "plain_text_domains",
                    },
                    {
                        "url": f"https://dns.google/resolve?name={competitor}&type=MX",
                        "parser": "dns_json",
                    },
                    {
                        "url": f"https://securitytrails.com/domain/{competitor}/dns",
                        "parser": "html_domain_extract",
                    },
                ]

                for source in public_sources:
                    if len(discovered) >= max_prospects:
                        break
                    try:
                        async with httpx.AsyncClient(
                            headers={
                                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                                "Accept": "text/plain,application/json,*/*",
                            },
                            timeout=httpx.Timeout(15),
                            follow_redirects=True,
                        ) as client:
                            resp = await client.get(source["url"])
                            if resp.status_code == 200:
                                import re
                                content = resp.text

                                if source["parser"] == "plain_text_domains":
                                    lines = content.strip().split("\n")
                                    for line in lines:
                                        if len(discovered) >= max_prospects:
                                            break

                                        line = line.strip()
                                        if not line or line.startswith("#"):
                                            continue

                                        domain_match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,})', line)
                                        if domain_match:
                                            dom = domain_match.group(1).lower()
                                            if dom in seen_domains:
                                                continue

                                            exclude = {"google.com", "bing.com", "youtube.com", "facebook.com", "twitter.com", "linkedin.com", "wikipedia.org", "amazon.com", competitor.lower()}
                                            if dom in exclude:
                                                continue
                                            if len(dom.split(".")) < 2:
                                                continue

                                            seen_domains.add(dom)
                                            da = calculate_local_authority(dom)
                                            if da < min_da:
                                                continue

                                            relevance = 0.72
                                            spam = 0.03
                                            composite = round(
                                                (da / 100.0) * 0.45 + relevance * 0.40 + (1.0 - spam) * 0.15, 4
                                            )

                                            discovered.append({
                                                "domain": dom,
                                                "url": f"https://{dom}/",
                                                "domain_authority": round(da, 1),
                                                "relevance_score": relevance,
                                                "spam_score": spam,
                                                "composite_score": composite,
                                                "source": "hackertarget_api",
                                            })

                                elif source["parser"] == "dns_json":
                                    import json
                                    try:
                                        dns_data = json.loads(content)
                                        if dns_data.get("Status") == 0:
                                            for record in dns_data.get("Answer", []):
                                                if len(discovered) >= max_prospects:
                                                    break
                                                dom = record.get("name", "").rstrip(".").lower()
                                                if not dom or dom in seen_domains or dom == competitor.lower():
                                                    continue
                                                if len(dom.split(".")) < 2:
                                                    continue

                                                seen_domains.add(dom)
                                                da = calculate_local_authority(dom)
                                                if da < min_da:
                                                    continue

                                                relevance = 0.68
                                                spam = 0.04
                                                composite = round(
                                                    (da / 100.0) * 0.45 + relevance * 0.40 + (1.0 - spam) * 0.15, 4
                                                )

                                                discovered.append({
                                                    "domain": dom,
                                                    "url": f"https://{dom}/",
                                                    "domain_authority": round(da, 1),
                                                    "relevance_score": relevance,
                                                    "spam_score": spam,
                                                    "composite_score": composite,
                                                    "source": "dns_google",
                                                })
                                    except json.JSONDecodeError:
                                        continue

                                elif source["parser"] == "html_domain_extract":
                                    domain_pattern = re.compile(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,})(?:/|$)')
                                    matches = domain_pattern.findall(content)

                                    exclude = {"google.com", "bing.com", "youtube.com", "facebook.com", "twitter.com", "linkedin.com", "wikipedia.org", "amazon.com", competitor.lower()}

                                    for match in matches:
                                        if len(discovered) >= max_prospects:
                                            break
                                        dom = match.lower()
                                        if dom in exclude or dom in seen_domains:
                                            continue
                                        if len(dom.split(".")) < 2:
                                            continue

                                        seen_domains.add(dom)
                                        da = calculate_local_authority(dom)
                                        if da < min_da:
                                            continue

                                        relevance = 0.70
                                        spam = 0.03
                                        composite = round(
                                            (da / 100.0) * 0.45 + relevance * 0.40 + (1.0 - spam) * 0.15, 4
                                        )

                                        discovered.append({
                                            "domain": dom,
                                            "url": f"https://{dom}/",
                                            "domain_authority": round(da, 1),
                                            "relevance_score": relevance,
                                            "spam_score": spam,
                                            "composite_score": composite,
                                            "source": "html_scrape",
                                        })
                    except Exception as e:
                        log.warning("public_source_failed", source=source["url"], error=str(e))
                        continue

        if not discovered:
            raise HTTPException(
                status_code=502,
                detail="No prospects found. All providers failed or returned empty results.",
            )

        persisted: list[DiscoveryProspectResponse] = []
        for item in discovered:
            existing = (
                await session.execute(
                    select(BacklinkProspect).where(
                        BacklinkProspect.tenant_id == request.tenant_id,
                        BacklinkProspect.campaign_id == campaign_id,
                        BacklinkProspect.domain == item["domain"],
                    )
                )
            ).scalar_one_or_none()

            if existing:
                persisted.append(DiscoveryProspectResponse(
                    domain=existing.domain,
                    domain_authority=existing.domain_authority,
                    relevance_score=existing.relevance_score,
                    spam_score=existing.spam_score,
                    composite_score=existing.composite_score,
                    source="existing",
                ))
                continue

            prospect = BacklinkProspect(
                tenant_id=request.tenant_id,
                campaign_id=campaign_id,
                domain=item["domain"],
                url=item["url"],
                status=ProspectStatus.NEW,
                domain_authority=item["domain_authority"],
                relevance_score=item["relevance_score"],
                spam_score=item["spam_score"],
                composite_score=item["composite_score"],
                confidence=round(item["composite_score"] * 0.95, 4),
                scoring_rationale={
                    "da_weight": 0.45,
                    "relevance_weight": 0.40,
                    "spam_weight": 0.15,
                    "min_da_filter": min_da,
                },
                page_data={"source": item["source"], "competitor": competitor_domains[0]},
            )
            session.add(prospect)
            persisted.append(DiscoveryProspectResponse(
                domain=item["domain"],
                domain_authority=item["domain_authority"],
                relevance_score=item["relevance_score"],
                spam_score=item["spam_score"],
                composite_score=item["composite_score"],
                source=item["source"],
            ))

        await session.flush()

        campaign.total_prospects = (
            await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id
                )
            )
        ).scalars().all().__len__()

        return APIResponse(
            data=DiscoveryResponse(
                campaign_id=str(campaign_id),
                prospects_discovered=len(persisted),
                prospects=persisted,
            )
        )


@router.post("/{campaign_id}/launch", response_model=APIResponse[CampaignLaunchResponse])
async def launch_campaign(campaign_id: UUID, tenant_id: UUID = Query(...)) -> APIResponse[CampaignLaunchResponse]:
    """Launch a campaign by starting the Temporal workflow."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.kill_switch import kill_switch_service
    from seo_platform.core.temporal_client import get_temporal_client
    from seo_platform.models.backlink import BacklinkCampaign
    from seo_platform.workflows.backlink_campaign import BacklinkCampaignInput

    kill_check = await kill_switch_service.is_blocked("all_outreach", tenant_id=tenant_id)
    if kill_check.blocked:
        raise HTTPException(status_code=503, detail=f"Kill switch active: {kill_check.reason}")

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(BacklinkCampaign).where(
                BacklinkCampaign.id == campaign_id,
                BacklinkCampaign.tenant_id == tenant_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        client = await get_temporal_client()

        workflow_input = BacklinkCampaignInput(
            tenant_id=tenant_id,
            client_id=campaign.client_id,
            campaign_id=campaign_id,
            campaign_name=campaign.name,
            campaign_type=campaign.campaign_type.value,
            competitor_domains=campaign.config.get("competitor_domains", []),
            target_link_count=campaign.target_link_count,
            min_domain_authority=campaign.config.get("min_domain_authority", 30.0),
            max_spam_score=campaign.config.get("max_spam_score", 5.0),
            initiated_by="api",
        )

        from seo_platform.workflows import TaskQueue
        handle = await client.start_workflow(
            "BacklinkCampaignWorkflow",
            workflow_input.model_dump_json(),
            id=f"backlink-campaign-{campaign_id}",
            task_queue=TaskQueue.BACKLINK_ENGINE,
        )

        campaign.workflow_run_id = handle.id
        campaign.status = "active"

        return APIResponse(
            data=CampaignLaunchResponse(
                campaign_id=str(campaign_id),
                workflow_run_id=handle.id,
                status="started",
            )
        )
