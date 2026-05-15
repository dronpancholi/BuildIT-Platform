"""
SEO Platform — Client Endpoints
==================================
Client CRUD with tenant isolation.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse, ResponseMeta

router = APIRouter()


class CreateClientRequest(BaseModel):
    tenant_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=4, max_length=255)
    niche: str | None = None
    business_type: str | None = None
    geo_focus: str | None = None
    competitors: str | None = None
    goals: list[str] = Field(default_factory=list)


class ClientResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    domain: str
    niche: str | None
    business_type: str | None
    onboarding_status: str
    created_at: datetime


@router.post("", response_model=APIResponse[ClientResponse], status_code=201)
async def create_client(request: CreateClientRequest) -> APIResponse[ClientResponse]:
    """Create a new client and trigger the onboarding workflow."""
    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.logging import get_logger
    from seo_platform.core.temporal_client import get_temporal_client
    from seo_platform.models.tenant import BusinessType, Client
    from seo_platform.workflows import OnboardingInput, TaskQueue

    logger = get_logger(__name__)

    async with get_tenant_session(request.tenant_id) as session:
        geo = [g.strip() for g in request.geo_focus.split(",") if g.strip()] if request.geo_focus else []
        comps = [c.strip() for c in request.competitors.split(",") if c.strip()] if request.competitors else []
        profile = {}
        if request.goals:
            profile["goals"] = request.goals

        client = Client(
            tenant_id=request.tenant_id,
            name=request.name,
            domain=request.domain,
            niche=request.niche,
            business_type=BusinessType(request.business_type) if request.business_type else None,
            geo_focus=geo,
            competitors=comps,
            profile_data=profile,
        )
        session.add(client)
        await session.flush()
        await session.refresh(client)

        # Trigger Temporal Onboarding Workflow
        try:
            temporal = await get_temporal_client()
            workflow_input = OnboardingInput(
                tenant_id=request.tenant_id,
                initiated_by="console_admin",
                client_id=client.id,
                domain=client.domain,
                business_name=client.name,
            )

            await temporal.start_workflow(
                "OnboardingWorkflow",
                args=[workflow_input.model_dump_json()],
                id=f"onboarding-{client.id}",
                task_queue=TaskQueue.ONBOARDING,
            )
            logger.info("onboarding_workflow_started", client_id=str(client.id))
        except Exception as e:
            logger.error("failed_to_start_onboarding_workflow", client_id=str(client.id), error=str(e))

        return APIResponse(
            data=ClientResponse(
                id=client.id,
                tenant_id=client.tenant_id,
                name=client.name,
                domain=client.domain,
                niche=client.niche,
                business_type=client.business_type.value if client.business_type else None,
                onboarding_status=client.onboarding_status.value,
                created_at=client.created_at,
            )
        )


@router.get("", response_model=APIResponse[list[ClientResponse]])
async def list_clients(
    tenant_id: UUID = Query(...),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> APIResponse[list[ClientResponse]]:
    """List all clients for a tenant with pagination."""
    from sqlalchemy import func, select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client

    async with get_tenant_session(tenant_id) as session:
        # Count
        count_result = await session.execute(
            select(func.count()).select_from(Client).where(Client.tenant_id == tenant_id)
        )
        total = count_result.scalar_one()

        # Fetch
        result = await session.execute(
            select(Client)
            .where(Client.tenant_id == tenant_id)
            .order_by(Client.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        clients = result.scalars().all()

        return APIResponse(
            data=[
                ClientResponse(
                    id=c.id,
                    tenant_id=c.tenant_id,
                    name=c.name,
                    domain=c.domain,
                    niche=c.niche,
                    business_type=c.business_type.value if c.business_type else None,
                    onboarding_status=c.onboarding_status.value,
                    created_at=c.created_at,
                )
                for c in clients
            ],
            meta=ResponseMeta(total=total, offset=offset, limit=limit, has_more=(offset + limit) < total),
        )


@router.post("/{client_id}/enrich")
async def enrich_client_profile(
    client_id: UUID,
    tenant_id: UUID = Query(...),
) -> APIResponse:
    """Auto-enrich client profile by scraping their website."""
    from seo_platform.core.logging import get_logger
    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client
    from sqlalchemy import select

    logger = get_logger(__name__)

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
        )
        client = result.scalar_one_or_none()
        if not client:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Client not found")

        domain = client.domain
        profile = client.profile_data or {}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(f"https://{domain}", follow_redirects=True)
                content = resp.text.lower() if resp.status_code == 200 else ""

                if content:
                    import re
                    title_match = re.search(r"<title>(.*?)</title>", content, re.DOTALL)
                    if title_match:
                        profile["site_title"] = title_match.group(1).strip()
                    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', content)
                    if desc_match:
                        profile["site_description"] = desc_match.group(1).strip()
                    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
                    if h1:
                        profile["headings"] = [h.strip() for h in h1[:5]]
                    words = re.findall(r'\b[a-z]{4,}\b', content)
                    from collections import Counter
                    common = Counter(words).most_common(20)
                    profile["top_keywords"] = [w for w, c in common if w not in ("this", "that", "with", "from", "your", "have", "will", "what", "about", "which", "their", "them", "been", "some", "would", "could", "there", "more")][:10]

                profile["last_analyzed"] = datetime.now().isoformat()
                client.profile_data = profile
                await session.commit()
                logger.info("client_enriched", client_id=str(client_id))

                return APIResponse(data={
                    "enriched": True,
                    "title": profile.get("site_title"),
                    "description": profile.get("site_description"),
                    "headings": profile.get("headings", []),
                    "top_keywords": profile.get("top_keywords", []),
                })
        except Exception as e:
            logger.warning("client_enrichment_failed", client_id=str(client_id), error=str(e))
            profile["last_analyzed"] = datetime.now().isoformat()
            profile["enrichment_error"] = str(e)
            client.profile_data = profile
            await session.commit()
            return APIResponse(data={"enriched": False, "error": str(e)})
