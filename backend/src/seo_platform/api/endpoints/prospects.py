"""
SEO Platform — Prospects Endpoint (Phase 1.5)
==============================================

Root-level `/prospects` endpoint used by the prospect-list dashboard page.
Returns the full BacklinkProspect schema (across all tenant campaigns)
mapped to the frontend's `Prospect` interface shape.

Previously the prospect-list page called `/prospects` and got 404 because
the only matching route was `/backlink-intelligence/prospects` (intelligence
view, not CRUD). This file adds the missing CRUD-shaped list endpoint.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from seo_platform.core.auth import get_validated_tenant_id
from seo_platform.schemas import APIResponse

router = APIRouter()


class ProspectResponse(BaseModel):
    id: str
    domain: str
    # BacklinkProspect has no separate email field; contact_email is the email.
    email: str | None = None
    # BacklinkProspect has no separate name field; contact_name is the name.
    name: str | None = None
    # BacklinkProspect has no company field; using domain as a placeholder.
    company: str | None = None
    domain_authority: float
    # BacklinkProspect has no page_authority field; use domain_authority as
    # a stand-in so the UI gets a non-null value.
    page_authority: float
    relevance_score: float
    composite_score: float
    # BacklinkProspect.status is a ProspectStatus enum with values
    # new/contacted/replied/converted/rejected — matches the UI exactly.
    status: str
    campaign_id: str
    campaign_name: str | None = None
    # BacklinkProspect has no last_contacted field.
    last_contacted: str | None = None
    # BacklinkProspect has no notes field.
    notes: str | None = None
    # BacklinkProspect has no tags field.
    tags: list[str] = []
    created_at: str | None = None


@router.get("/prospects", response_model=APIResponse[list[ProspectResponse]])
async def list_prospects(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None, description="Filter by prospect status"),
) -> APIResponse[list[ProspectResponse]]:
    """List all BacklinkProspect records for the tenant, mapped to UI shape."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkProspect, BacklinkCampaign

    async with get_tenant_session(tenant_id) as session:
        # Look up campaign IDs for this tenant.
        camp_res = await session.execute(
            select(BacklinkCampaign.id, BacklinkCampaign.name).where(
                BacklinkCampaign.tenant_id == tenant_id
            )
        )
        campaigns = {row.id: row.name for row in camp_res.all()}

        if not campaigns:
            return APIResponse(data=[])

        campaign_ids = list(campaigns.keys())

        # Build the prospect query scoped to those campaigns.
        query = select(BacklinkProspect).where(
            BacklinkProspect.campaign_id.in_(campaign_ids)
        )
        if status:
            # BacklinkProspect.status is a ProspectStatus enum whose values
            # are the lowercase strings ("new", "contacted", "replied",
            # "converted", "rejected") — match against the .value.
            query = query.where(BacklinkProspect.status == status)

        query = query.order_by(
            BacklinkProspect.composite_score.desc().nullslast(),
            BacklinkProspect.created_at.desc().nullslast(),
        ).limit(limit).offset(offset)

        result = await session.execute(query)
        prospects = result.scalars().all()

        data = [
            ProspectResponse(
                id=str(p.id),
                domain=p.domain,
                email=p.contact_email,
                name=p.contact_name,
                company=p.domain,  # Domain stands in for company.
                domain_authority=p.domain_authority or 0.0,
                page_authority=p.domain_authority or 0.0,  # Use DA as PA stand-in.
                relevance_score=p.relevance_score or 0.0,
                composite_score=p.composite_score or 0.0,
                status=p.status.value if hasattr(p.status, "value") else str(p.status),
                campaign_id=str(p.campaign_id),
                campaign_name=campaigns.get(p.campaign_id),
                created_at=p.created_at.isoformat() if p.created_at else None,
            )
            for p in prospects
        ]
        return APIResponse(data=data)


@router.get("/prospects/stats", response_model=APIResponse[dict[str, Any]])
async def get_prospects_stats(
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> APIResponse[dict[str, Any]]:
    """Aggregate counts and score distributions for the prospect-list UI."""
    from sqlalchemy import func, select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkProspect, BacklinkCampaign

    async with get_tenant_session(tenant_id) as session:
        camp_res = await session.execute(
            select(BacklinkCampaign.id).where(BacklinkCampaign.tenant_id == tenant_id)
        )
        campaign_ids = [row for row in camp_res.scalars().all()]

        if not campaign_ids:
            return APIResponse(data={
                "total": 0,
                "by_status": {},
                "avg_composite_score": 0.0,
                "avg_domain_authority": 0.0,
            })

        # Aggregate by status.
        status_res = await session.execute(
            select(BacklinkProspect.status, func.count())
            .where(BacklinkProspect.campaign_id.in_(campaign_ids))
            .group_by(BacklinkProspect.status)
        )
        by_status = {
            (s.value if hasattr(s, "value") else str(s)): cnt
            for s, cnt in status_res.all()
        }

        # Aggregate score averages.
        score_res = await session.execute(
            select(
                func.avg(BacklinkProspect.composite_score),
                func.avg(BacklinkProspect.domain_authority),
                func.count(),
            )
            .where(BacklinkProspect.campaign_id.in_(campaign_ids))
        )
        avg_composite, avg_da, total = score_res.one()
        return APIResponse(data={
            "total": int(total or 0),
            "by_status": by_status,
            "avg_composite_score": float(avg_composite or 0.0),
            "avg_domain_authority": float(avg_da or 0.0),
        })
