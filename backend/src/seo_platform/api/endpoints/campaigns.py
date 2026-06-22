# PHASE 1.2 — Simulation removed: simulate_thread_reply and mark_link_acquired endpoints
"""
SEO Platform — Campaign Endpoints
=====================================
Campaign management with workflow triggering.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from seo_platform.core.auth import CurrentUser, get_validated_tenant_id, validate_tenant_id
from seo_platform.core.rbac import RequirePermission
from seo_platform.models.backlink import CampaignStatus
from seo_platform.schemas import APIResponse, ResponseMeta
from seo_platform.models.backlink import CampaignStatus

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
    tenant_id: UUID = Depends(get_validated_tenant_id),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _auth: None = Depends(RequirePermission("campaigns:read")),
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
async def create_campaign(
    request: CreateCampaignRequest,
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[CampaignResponse]:
    """Create a new backlink campaign (draft status)."""
    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign, CampaignType
    from seo_platform.services.audit_logger import audit_logger

    # Validate tenant_id matches authenticated user
    await validate_tenant_id(request.tenant_id, user=_auth)

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
        try:
            await session.flush()
        except IntegrityError as e:
            await session.rollback()
            if "foreign key" in str(e.orig).lower() or "referential integrity" in str(e.orig).lower():
                raise HTTPException(status_code=400, detail=f"Client with ID '{request.client_id}' does not exist for this tenant")
            raise HTTPException(status_code=400, detail=f"Invalid request data: {e.orig}")
        await session.refresh(campaign)

        # Audit log
        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(request.tenant_id),
            user_id=user_id,
            action="campaign.create",
            entity_type="campaign",
            entity_id=str(campaign.id),
            after={"name": campaign.name, "type": campaign.campaign_type.value, "status": campaign.status.value},
        )

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
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
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
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
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
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
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
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[SendThreadResponse]:
    """Send a draft email thread via MailHog SMTP."""
    from datetime import datetime, timezone

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import OutreachThread, ThreadStatus
    from seo_platform.services.email_provider import get_email_provider

    async with get_tenant_session(tenant_id) as session:
        thread = await session.get(OutreachThread, thread_id)
        if not thread or thread.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.status not in (ThreadStatus.DRAFT, ThreadStatus.QUEUED):
            raise HTTPException(status_code=400, detail=f"Cannot send thread in {thread.status} status")

        provider = get_email_provider()
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
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[ScheduleFollowUpResponse]:
    """Schedule and send a follow-up email for a thread."""
    from datetime import datetime, timezone

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import OutreachThread, ThreadStatus
    from seo_platform.services.email_provider import get_email_provider

    async with get_tenant_session(tenant_id) as session:
        thread = await session.get(OutreachThread, thread_id)
        if not thread or thread.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.status not in (ThreadStatus.SENT, ThreadStatus.REPLIED):
            raise HTTPException(status_code=400, detail=f"Cannot follow up thread in {thread.status} status")

        follow_up_subject = request.follow_up_subject or f"Re: {thread.subject}"
        provider = get_email_provider()
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


@router.post("/{campaign_id}/cancel", response_model=APIResponse[CampaignResponse])
async def cancel_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[CampaignResponse]:
    """Cancel a backlink campaign."""
    from datetime import datetime, timezone

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

        campaign.status = CampaignStatus.CANCELLED
        campaign.updated_at = datetime.now(timezone.utc)
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


@router.get("/{campaign_id}", response_model=APIResponse[CampaignResponse])
async def get_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
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
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
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
            from seo_platform.core.sanitization import sanitize_string
            campaign.name = sanitize_string(request.name)
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


@router.delete("/{campaign_id}", response_model=APIResponse)
async def delete_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse:
    """Delete a backlink campaign and its associated prospects/threads."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign
    from seo_platform.services.audit_logger import audit_logger

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

        before = {"name": campaign.name, "status": campaign.status.value}
        await session.delete(campaign)
        await session.flush()

        # Audit log
        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="campaign.delete",
            entity_type="campaign",
            entity_id=str(campaign_id),
            before=before,
        )

        return APIResponse(data={"deleted": True, "campaign_id": str(campaign_id)})


class GenerateEmailRequest(BaseModel):
    tenant_id: UUID | None = None


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
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
    validated_tenant_id: UUID = Depends(get_validated_tenant_id),
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

    # Validate tenant_id matches authenticated user; fall back to
    # the validated tenant from the auth context if the caller did
    # not include tenant_id in the body.
    effective_tenant_id = request.tenant_id or validated_tenant_id
    await validate_tenant_id(effective_tenant_id, user=_auth)

    settings = get_settings()
    use_nim = settings.nvidia.api_key and "mock" not in settings.nvidia.api_key.lower()

    async with get_tenant_session(effective_tenant_id) as session:
        campaign = await session.get(BacklinkCampaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        prospects = (
            await session.execute(
                select(BacklinkProspect)
                .where(
                    BacklinkProspect.campaign_id == campaign_id,
                    BacklinkProspect.tenant_id == effective_tenant_id,
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
                tenant_id=effective_tenant_id,
                email_body=body,
                entity_id=prospect.id,
                entity_type="email_pitch",
            )

            thread = OutreachThread(
                tenant_id=effective_tenant_id,
                campaign_id=campaign_id,
                prospect_id=prospect.id,
                status=ThreadStatus.DRAFT,
                from_email=f"outreach@{campaign.target_domain or 'yourdomain.com'}",
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
    tenant_id: UUID | None = None
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
    _auth: CurrentUser = Depends(RequirePermission("campaigns:write")),
    validated_tenant_id: UUID = Depends(get_validated_tenant_id),
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

    # Validate tenant_id matches authenticated user; fall back to
    # the validated tenant from the auth context if the caller did
    # not include tenant_id in the body.
    effective_tenant_id = request.tenant_id or validated_tenant_id
    await validate_tenant_id(effective_tenant_id, user=_auth)

    async with get_tenant_session(effective_tenant_id) as session:
        campaign = await session.get(BacklinkCampaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        competitor_domains = campaign.config.get("competitor_domains", [])
        if not competitor_domains:
            # Use the client's own domain as fallback
            if campaign.client and campaign.client.domain:
                competitor_domains = [campaign.client.domain]
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Campaign has no competitor_domains configured and no client domain available",
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
                        BacklinkProspect.tenant_id == effective_tenant_id,
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
                tenant_id=effective_tenant_id,
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

        try:
            from seo_platform.core.metrics import prospects_discovered as _pd
            _pd.labels(tenant_id=str(effective_tenant_id)).inc(len(persisted))
        except Exception:
            pass

        return APIResponse(
            data=DiscoveryResponse(
                campaign_id=str(campaign_id),
                prospects_discovered=len(persisted),
                prospects=persisted,
            )
        )


@router.post("/{campaign_id}/launch", response_model=APIResponse[CampaignLaunchResponse])
async def launch_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[CampaignLaunchResponse]:
    """Launch a campaign by starting the Temporal workflow."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.kill_switch import kill_switch_service
    from seo_platform.core.temporal_client import get_temporal_client
    from seo_platform.models.backlink import BacklinkCampaign
    from seo_platform.services.audit_logger import audit_logger
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

        # Audit log
        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="campaign.launch",
            entity_type="campaign",
            entity_id=str(campaign_id),
            after={"status": "active", "workflow_run_id": handle.id},
        )

        return APIResponse(
            data=CampaignLaunchResponse(
                campaign_id=str(campaign_id),
                workflow_run_id=handle.id,
                status="started",
            )
        )


# Phase 1.1 — lifecycle transitions
# Frontend pause/resume/archive buttons POST to these endpoints.
# PUT /campaigns/{id} ignores the status field (it only updates
# name, type, target_link_count, config), so without these
# dedicated routes the user clicks Pause, gets a 200 success toast,
# and the status does not actually change. Pure silent no-op.
_PAUSE_ALLOWED_FROM = {
    CampaignStatus.DRAFT,
    CampaignStatus.ACTIVE,
    CampaignStatus.AWAITING_APPROVAL,
    CampaignStatus.MONITORING,
    CampaignStatus.PROSPECTING,
    CampaignStatus.SCORING,
    CampaignStatus.OUTREACH_PREP,
}
_RESUME_ALLOWED_FROM = {
    CampaignStatus.PAUSED,
    CampaignStatus.MONITORING,
    CampaignStatus.PROSPECTING,
    CampaignStatus.SCORING,
    CampaignStatus.OUTREACH_PREP,
}
_ARCHIVE_ALLOWED_FROM = set(CampaignStatus)


def _transition_campaign(
    campaign: BacklinkCampaign,
    target: CampaignStatus,
    allowed_from: set[CampaignStatus],
) -> None:
    """Validate transition and apply. Raises 409 on invalid source state."""
    if campaign.status not in allowed_from:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot transition campaign from '{campaign.status.value}' "
                f"to '{target.value}'."
            ),
        )
    campaign.status = target


@router.post("/{campaign_id}/pause", response_model=APIResponse[CampaignResponse])
async def pause_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[CampaignResponse]:
    """Pause a running or awaiting-approval campaign."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign
    from seo_platform.services.audit_logger import audit_logger

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

        _transition_campaign(campaign, CampaignStatus.PAUSED, _PAUSE_ALLOWED_FROM)
        await session.flush()
        await session.refresh(campaign)

        # Audit log
        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="campaign.pause",
            entity_type="campaign",
            entity_id=str(campaign_id),
            after={"status": "paused"},
        )

        return APIResponse(
            data=CampaignResponse(
                id=campaign.id,
                tenant_id=campaign.tenant_id,
                client_id=campaign.client_id,
                client_name=campaign.client.name if campaign.client else None,
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


@router.post("/{campaign_id}/resume", response_model=APIResponse[CampaignResponse])
async def resume_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[CampaignResponse]:
    """Resume a paused campaign back to active."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign
    from seo_platform.services.audit_logger import audit_logger

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

        _transition_campaign(campaign, CampaignStatus.ACTIVE, _RESUME_ALLOWED_FROM)
        await session.flush()
        await session.refresh(campaign)

        # Audit log
        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="campaign.resume",
            entity_type="campaign",
            entity_id=str(campaign_id),
            after={"status": "active"},
        )

        return APIResponse(
            data=CampaignResponse(
                id=campaign.id,
                tenant_id=campaign.tenant_id,
                client_id=campaign.client_id,
                client_name=campaign.client.name if campaign.client else None,
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


@router.post("/{campaign_id}/archive", response_model=APIResponse[CampaignResponse])
async def archive_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[CampaignResponse]:
    """Archive a campaign. Reversible via PUT update."""
    from sqlalchemy import text

    from seo_platform.core.database import get_tenant_session
    from seo_platform.services.audit_logger import audit_logger

    # The 'archived' value was added to the campaign_status enum via
    # `ALTER TYPE ... ADD VALUE` outside this session. asyncpg's prepared
    # statement cache can lag the enum definition, so we bypass SQLAlchemy
    # ORM entirely and use a raw CAST(text AS enum) which the driver
    # accepts without consulting its cached enum array.
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            text(
                "UPDATE backlink_campaigns "
                "SET status = CAST(:new_status AS campaign_status), "
                "    updated_at = NOW() "
                "WHERE id = :cid AND tenant_id = :tid "
                "RETURNING id, tenant_id, client_id, name, campaign_type, "
                "          status, target_link_count, acquired_link_count, "
                "          health_score, workflow_run_id, created_at, updated_at"
            ),
            {
                "new_status": CampaignStatus.ARCHIVED.value,
                "cid": str(campaign_id),
                "tid": str(tenant_id),
            },
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Audit log
        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="campaign.archive",
            entity_type="campaign",
            entity_id=str(campaign_id),
            after={"status": "archived"},
        )

        # Look up client name separately (no ORM mapping needed).
        client_name = None
        if row.get("client_id"):
            cn = await session.execute(
                text("SELECT name FROM clients WHERE id = :cid"),
                {"cid": str(row["client_id"])},
            )
            client_row = cn.mappings().first()
            if client_row:
                client_name = client_row["name"]

        return APIResponse(
            data=CampaignResponse(
                id=row["id"],
                tenant_id=row["tenant_id"],
                client_id=row["client_id"],
                client_name=client_name,
                name=row["name"],
                campaign_type=row["campaign_type"],
                status=row["status"],
                target_link_count=row["target_link_count"],
                acquired_link_count=row["acquired_link_count"],
                health_score=row["health_score"],
                workflow_run_id=row["workflow_run_id"],
                created_at=row["created_at"].isoformat() if row["created_at"] else None,
                updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
            )
        )

        return APIResponse(
            data=CampaignResponse(
                id=campaign.id,
                tenant_id=campaign.tenant_id,
                client_id=campaign.client_id,
                client_name=campaign.client.name if campaign.client else None,
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
