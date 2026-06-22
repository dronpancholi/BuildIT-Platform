"""
SEO Platform — Client Endpoints
==================================
Client CRUD with tenant isolation.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any

from seo_platform.core.auth import CurrentUser, get_validated_tenant_id, validate_tenant_id
from seo_platform.core.rbac import RequirePermission
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
    geo_focus: list[str]
    competitors: list[str]
    profile_data: dict[str, Any]
    onboarding_status: str
    status: str
    archived_at: datetime | None = None
    keyword_count: int = 0
    campaign_count: int = 0
    created_at: datetime


@router.get("/{client_id}", response_model=APIResponse[ClientResponse])
async def get_client(
    client_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("customers:read")),
) -> APIResponse[ClientResponse]:
    """Get a single client by ID."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
            )
        )
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        return APIResponse(
            data=ClientResponse(
                id=client.id,
                tenant_id=client.tenant_id,
                name=client.name,
                domain=client.domain,
                niche=client.niche,
                business_type=client.business_type.value if client.business_type else None,
                geo_focus=client.geo_focus or [],
                competitors=client.competitors or [],
                profile_data=client.profile_data or {},
                onboarding_status=client.onboarding_status.value,
                status=client.status.value,
                archived_at=client.archived_at,
                keyword_count=0,
                campaign_count=0,
                created_at=client.created_at,
            )
        )


class CampaignSummaryResponse(BaseModel):
    id: UUID
    name: str
    campaign_type: str
    status: str
    target_link_count: int
    acquired_link_count: int
    total_prospects: int
    total_emails_sent: int
    reply_rate: float
    acquisition_rate: float
    health_score: float
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


@router.get("/{client_id}/campaigns", response_model=APIResponse[list[CampaignSummaryResponse]])
async def list_client_campaigns(
    client_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("customers:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None, description="Filter by campaign status"),
) -> APIResponse[list[CampaignSummaryResponse]]:
    """List all backlink campaigns belonging to a single client (GAP-004, Phase 1.4)."""
    from sqlalchemy import select, func

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client
    from seo_platform.models.backlink import BacklinkCampaign, CampaignStatus

    async with get_tenant_session(tenant_id) as session:
        # 1) Tenant-scoped client existence check (no cross-tenant leakage).
        client_result = await session.execute(
            select(Client.id).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
            )
        )
        if client_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Client not found")

        # 2) Tenant-scoped campaign query scoped to the client.
        query = select(BacklinkCampaign).where(
            BacklinkCampaign.client_id == client_id,
            BacklinkCampaign.tenant_id == tenant_id,
        )
        if status:
            # Accept both enum names (DRAFT) and values (draft); case-insensitive.
            normalized = status.strip().upper()
            try:
                status_enum = CampaignStatus[normalized]
            except KeyError:
                valid = [s.name for s in CampaignStatus]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status '{status}'. Valid: {valid}",
                )
            query = query.where(BacklinkCampaign.status == status_enum)
        query = query.order_by(BacklinkCampaign.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(query)
        campaigns = result.scalars().all()

        data = [
            CampaignSummaryResponse(
                id=c.id,
                name=c.name,
                campaign_type=c.campaign_type.value if hasattr(c.campaign_type, "value") else str(c.campaign_type),
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                target_link_count=c.target_link_count,
                acquired_link_count=c.acquired_link_count,
                total_prospects=c.total_prospects,
                total_emails_sent=c.total_emails_sent,
                reply_rate=c.reply_rate,
                acquisition_rate=c.acquisition_rate,
                health_score=c.health_score,
                started_at=c.started_at,
                completed_at=c.completed_at,
                created_at=c.created_at,
            )
            for c in campaigns
        ]
        return APIResponse(data=data, meta=ResponseMeta(count=len(data)))


class UpdateClientRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, min_length=4, max_length=255)
    niche: str | None = None
    business_type: str | None = None
    geo_focus: str | None = None
    competitors: str | None = None
    goals: list[str] | None = None


@router.put("/{client_id}", response_model=APIResponse[ClientResponse])
async def update_client(
    client_id: UUID,
    request: UpdateClientRequest,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("customers:write")),
) -> APIResponse[ClientResponse]:
    """Update an existing client."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.sanitization import sanitize_string
    from seo_platform.models.tenant import BusinessType, Client
    from seo_platform.services.audit_logger import audit_logger

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
            )
        )
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if request.name is not None:
            client.name = sanitize_string(request.name)
        if request.domain is not None:
            client.domain = request.domain
        if request.niche is not None:
            client.niche = sanitize_string(request.niche) if request.niche else None
        if request.business_type is not None:
            client.business_type = BusinessType(request.business_type) if request.business_type else None
        if request.geo_focus is not None:
            client.geo_focus = [g.strip() for g in request.geo_focus.split(",") if g.strip()] if request.geo_focus else []
        if request.competitors is not None:
            client.competitors = [c.strip() for c in request.competitors.split(",") if c.strip()] if request.competitors else []
        if request.goals is not None:
            profile = client.profile_data or {}
            profile["goals"] = request.goals
            client.profile_data = profile

        try:
            await session.flush()
        except Exception as flush_err:
            await session.rollback()
            if "unique" in str(flush_err).lower() or "duplicate" in str(flush_err).lower():
                raise HTTPException(status_code=409, detail=f"Client with domain '{request.domain}' already exists for this tenant")
            raise HTTPException(status_code=500, detail=f"Failed to update client: {flush_err!s}")
        await session.refresh(client)

        # Audit log
        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="client.update",
            entity_type="client",
            entity_id=str(client.id),
            after={"name": client.name, "domain": client.domain, "status": client.onboarding_status.value},
        )

        return APIResponse(
            data=ClientResponse(
                id=client.id,
                tenant_id=client.tenant_id,
                name=client.name,
                domain=client.domain,
                niche=client.niche,
                business_type=client.business_type.value if client.business_type else None,
                geo_focus=client.geo_focus or [],
                competitors=client.competitors or [],
                profile_data=client.profile_data or {},
                onboarding_status=client.onboarding_status.value,
                status=client.status.value,
                archived_at=client.archived_at,
                keyword_count=0,
                campaign_count=0,
                created_at=client.created_at,
            )
        )


@router.delete("/{client_id}", response_model=APIResponse)
async def delete_client(
    client_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("customers:write")),
) -> APIResponse:
    """Soft-delete (archive) a client."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client, ClientStatus
    from seo_platform.services.audit_logger import audit_logger

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
            )
        )
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        before = {"name": client.name, "status": client.onboarding_status.value}
        client.status = ClientStatus.ARCHIVED
        client.archived_at = datetime.now()
        await session.flush()

        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="client.archive",
            entity_type="client",
            entity_id=str(client.id),
            before=before,
            after={"status": "archived"},
        )

        return APIResponse(data={"archived": True, "client_id": str(client_id)})


@router.post("/{client_id}/archive", response_model=APIResponse)
async def archive_client(
    client_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("customers:write")),
) -> APIResponse:
    """Archive a client (soft delete)."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client, ClientStatus
    from seo_platform.services.audit_logger import audit_logger

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
            )
        )
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if client.status == ClientStatus.ARCHIVED:
            raise HTTPException(status_code=400, detail="Client is already archived")

        before = {"name": client.name, "status": client.onboarding_status.value}
        client.status = ClientStatus.ARCHIVED
        client.archived_at = datetime.now()
        await session.flush()

        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="client.archive",
            entity_type="client",
            entity_id=str(client.id),
            before=before,
            after={"status": "archived"},
        )

        return APIResponse(data={"archived": True, "client_id": str(client_id)})


@router.post("/{client_id}/restore", response_model=APIResponse)
async def restore_client(
    client_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("customers:write")),
) -> APIResponse:
    """Restore an archived client."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client, ClientStatus
    from seo_platform.services.audit_logger import audit_logger

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Client).where(
                Client.id == client_id,
                Client.tenant_id == tenant_id,
            )
        )
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if client.status == ClientStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Client is already active")

        before = {"status": client.onboarding_status.value}
        client.status = ClientStatus.ACTIVE
        client.archived_at = None
        await session.flush()

        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(tenant_id),
            user_id=user_id,
            action="client.restore",
            entity_type="client",
            entity_id=str(client.id),
            before=before,
            after={"status": "active"},
        )

        return APIResponse(data={"restored": True, "client_id": str(client_id)})


@router.post("", response_model=APIResponse[ClientResponse], status_code=201)
async def create_client(
    request: CreateClientRequest,
    _auth: CurrentUser = Depends(RequirePermission("customers:write")),
) -> APIResponse[ClientResponse]:
    """Create a new client and trigger the onboarding workflow."""
    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.logging import get_logger
    from seo_platform.core.sanitization import sanitize_string
    from seo_platform.core.temporal_client import get_temporal_client
    from seo_platform.models.tenant import BusinessType, Client
    from seo_platform.services.audit_logger import audit_logger
    from seo_platform.workflows import OnboardingInput, TaskQueue

    logger = get_logger(__name__)
    logger.info("create_client_request", name=request.name, domain=request.domain, business_type=request.business_type, tenant_id=str(request.tenant_id))

    request.name = sanitize_string(request.name)
    if request.niche:
        request.niche = sanitize_string(request.niche)
    if request.business_type:
        request.business_type = sanitize_string(request.business_type)
    if request.geo_focus:
        request.geo_focus = sanitize_string(request.geo_focus)
    if request.competitors:
        request.competitors = sanitize_string(request.competitors)

    # Validate tenant_id matches authenticated user
    await validate_tenant_id(request.tenant_id, user=_auth)

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
        try:
            await session.flush()
        except Exception as flush_err:
            await session.rollback()
            if "unique" in str(flush_err).lower() or "duplicate" in str(flush_err).lower():
                raise HTTPException(status_code=409, detail=f"Client with domain '{request.domain}' already exists for this tenant")
            raise HTTPException(status_code=500, detail=f"Failed to create client: {flush_err!s}")
        await session.refresh(client)

        # Audit log
        user_id = str(_auth.id) if hasattr(_auth, "id") else "system"
        await audit_logger.log(
            tenant_id=str(request.tenant_id),
            user_id=user_id,
            action="client.create",
            entity_type="client",
            entity_id=str(client.id),
            after={"name": client.name, "domain": client.domain, "status": client.onboarding_status.value},
        )

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
                geo_focus=client.geo_focus or [],
                competitors=client.competitors or [],
                profile_data=client.profile_data or {},
                onboarding_status=client.onboarding_status.value,
                status=client.status.value,
                archived_at=client.archived_at,
                keyword_count=0,
                campaign_count=0,
                created_at=client.created_at,
            )
        )


@router.get("", response_model=APIResponse[list[ClientResponse]])
async def list_clients(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None, description="Filter by client status: active or archived"),
    _auth: None = Depends(RequirePermission("customers:read")),
) -> APIResponse[list[ClientResponse]]:
    """List all clients for a tenant with pagination and optional status filter."""
    from sqlalchemy import func, select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client, ClientStatus

    async with get_tenant_session(tenant_id) as session:
        base_query = select(Client).where(Client.tenant_id == tenant_id)

        if status:
            normalized = status.strip().lower()
            try:
                status_enum = ClientStatus(normalized)
            except ValueError:
                valid = [s.value for s in ClientStatus]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status '{status}'. Valid: {valid}",
                )
            base_query = base_query.where(Client.status == status_enum)

        # Count
        count_result = await session.execute(
            select(func.count()).select_from(Client).where(
                Client.tenant_id == tenant_id,
                *([Client.status == ClientStatus(status.strip().lower())] if status else []),
            )
        )
        total = count_result.scalar_one()

        # Fetch
        result = await session.execute(
            base_query.order_by(Client.created_at.desc()).offset(offset).limit(limit)
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
                    geo_focus=c.geo_focus or [],
                    competitors=c.competitors or [],
                    profile_data=c.profile_data or {},
                    onboarding_status=c.onboarding_status.value,
                    status=c.status.value,
                    archived_at=c.archived_at,
                    keyword_count=0,
                    campaign_count=0,
                    created_at=c.created_at,
                )
                for c in clients
            ],
            meta=ResponseMeta(total=total, offset=offset, limit=limit, has_more=(offset + limit) < total),
        )


def _is_safe_url(url: str) -> bool:
    """Check if URL is safe to fetch (no SSRF)."""
    import ipaddress
    import re
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass
        ip_prefix = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', hostname)
        if ip_prefix:
            try:
                ip = ipaddress.ip_address(ip_prefix.group(1))
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
            except ValueError:
                pass
        if hostname.endswith(".internal") or hostname.endswith(".local"):
            return False
        if hostname in ("169.254.169.254", "metadata.google.internal"):
            return False
        return True
    except Exception:
        return False


@router.post("/{client_id}/enrich")
async def enrich_client_profile(
    client_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("customers:write")),
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

        url = f"https://{domain}"
        if not _is_safe_url(url):
            return APIResponse(data={"enriched": False, "error": "Domain not allowed (SSRF protection)"})

        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(url, follow_redirects=True)
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
