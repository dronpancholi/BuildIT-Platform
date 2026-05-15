"""
SEO Platform — Campaign Endpoints
=====================================
Campaign management with workflow triggering.
"""

from __future__ import annotations

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
