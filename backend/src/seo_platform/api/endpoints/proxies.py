"""
SEO Platform — Proxy Pool & Rate Limit API Endpoints
=====================================================
REST endpoints for proxy management and rate limit configuration.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.schemas import APIResponse
from seo_platform.services.proxy_manager import proxy_manager
from seo_platform.services.rate_limiter import rate_limiter

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class ProxyCreateRequest(BaseModel):
    """Request to add a new proxy."""

    name: str = Field(..., min_length=1, max_length=100)
    proxy_type: str = Field(..., pattern="^(residential|datacenter|mobile|shared)$")
    proxy_host: str = Field(..., min_length=1, max_length=255)
    proxy_port: int = Field(..., gt=0, le=65535)
    proxy_protocol: str = Field("http", pattern="^(http|https|socks5|socks4)$")
    proxy_auth_username: str | None = None
    proxy_auth_password: str | None = None
    assigned_sites: list[str] = Field(default_factory=list)


class RateLimitUpdateRequest(BaseModel):
    """Request to update rate limits."""

    requests_per_minute: int | None = Field(None, ge=1, le=1000)
    requests_per_hour: int | None = Field(None, ge=1, le=100000)
    requests_per_day: int | None = Field(None, ge=1, le=10000000)
    max_retries: int | None = Field(None, ge=0, le=10)
    backoff_multiplier: float | None = Field(None, ge=1.0, le=10.0)
    max_captchas_before_skip: int | None = Field(None, ge=0, le=20)


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class ProxyResponse(BaseModel):
    """Response schema for a proxy."""

    id: uuid.UUID
    name: str
    proxy_type: str
    proxy_host: str
    proxy_port: int
    proxy_protocol: str
    status: str
    health_score: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    assigned_sites: list[str] | None = None

    model_config = {"from_attributes": True}


class ProxySummaryResponse(BaseModel):
    """Summary stats for proxy pool dashboard."""

    total: int
    active: int
    suspended: int
    expired: int
    avg_health: int
    total_requests: int
    success_rate: float


class ProxyListResponse(BaseModel):
    """List of proxies with summary."""

    proxies: list[ProxyResponse]
    summary: ProxySummaryResponse


class RateLimitCheckResponse(BaseModel):
    """Response from rate limit check."""

    allowed: bool
    wait_seconds: float
    remaining: dict


# ---------------------------------------------------------------------------
# GET /proxies/pools
# ---------------------------------------------------------------------------
@router.get("/pools", response_model=APIResponse[ProxyListResponse])
async def list_proxies(
    status: str | None = None,
    proxy_type: str | None = None,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ProxyListResponse]:
    """List all proxy pools."""
    async with get_session() as session:
        proxies = await proxy_manager.list_proxies(
            session, tenant_id, status=status, proxy_type=proxy_type
        )
        summary = await proxy_manager.get_proxy_summary(session, tenant_id)

    return APIResponse(
        data=ProxyListResponse(
            proxies=[ProxyResponse.model_validate(p) for p in proxies],
            summary=ProxySummaryResponse(**summary),
        )
    )


# ---------------------------------------------------------------------------
# POST /proxies/pools
# ---------------------------------------------------------------------------
@router.post("/pools", response_model=APIResponse[ProxyResponse])
async def add_proxy(
    request: ProxyCreateRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ProxyResponse]:
    """Add new proxy to pool."""
    async with get_session() as session:
        proxy = await proxy_manager.add_proxy(
            session=session,
            tenant_id=tenant_id,
            name=request.name,
            proxy_type=request.proxy_type,
            proxy_host=request.proxy_host,
            proxy_port=request.proxy_port,
            proxy_protocol=request.proxy_protocol,
            proxy_auth_username=request.proxy_auth_username,
            proxy_auth_password=request.proxy_auth_password,
            assigned_sites=request.assigned_sites,
        )

    return APIResponse(data=ProxyResponse.model_validate(proxy))


# ---------------------------------------------------------------------------
# GET /proxies/pools/{id}
# ---------------------------------------------------------------------------
@router.get("/pools/{proxy_id}", response_model=APIResponse[ProxyResponse])
async def get_proxy(
    proxy_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ProxyResponse]:
    """Get proxy details."""
    async with get_session() as session:
        proxy = await proxy_manager.get_proxy_by_id(session, proxy_id, tenant_id)
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")

    return APIResponse(data=ProxyResponse.model_validate(proxy))


# ---------------------------------------------------------------------------
# DELETE /proxies/pools/{id}
# ---------------------------------------------------------------------------
@router.delete("/pools/{proxy_id}", response_model=APIResponse[dict])
async def delete_proxy(
    proxy_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Remove proxy from pool."""
    async with get_session() as session:
        deleted = await proxy_manager.delete_proxy(session, proxy_id, tenant_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Proxy not found")

    return APIResponse(data={"deleted": True})


# ---------------------------------------------------------------------------
# POST /proxies/pools/{id}/blacklist
# ---------------------------------------------------------------------------
@router.post("/pools/{proxy_id}/blacklist", response_model=APIResponse[dict])
async def blacklist_proxy(
    proxy_id: uuid.UUID,
    reason: str = "Manual blacklist",
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Manually blacklist a proxy."""
    async with get_session() as session:
        blacklisted = await proxy_manager.blacklist_proxy(session, proxy_id, reason)
        if not blacklisted:
            raise HTTPException(status_code=404, detail="Proxy not found")

    return APIResponse(data={"blacklisted": True})


# ---------------------------------------------------------------------------
# POST /proxies/pools/{id}/test
# ---------------------------------------------------------------------------
@router.post("/pools/{proxy_id}/test", response_model=APIResponse[dict])
async def test_proxy(
    proxy_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Test proxy connectivity."""
    import time
    import httpx

    start = time.time()
    async with get_session() as session:
        proxy = await proxy_manager.get_proxy_by_id(session, proxy_id, tenant_id)
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")

        proxy_url = f"{proxy.proxy_protocol}://{proxy.proxy_host}:{proxy.proxy_port}"
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url, timeout=10.0
            ) as client:
                resp = await client.get("https://httpbin.org/ip")
                elapsed_ms = (time.time() - start) * 1000
                success = resp.status_code == 200
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            success = False

    return APIResponse(
        data={
            "success": success,
            "proxy_id": str(proxy_id),
            "response_time_ms": round(elapsed_ms, 2),
        }
    )


# ---------------------------------------------------------------------------
# GET /rate-limits/check
# ---------------------------------------------------------------------------
@router.get("/rate-limits/check", response_model=APIResponse[RateLimitCheckResponse])
async def check_rate_limit(
    site: str,
    credential_id: str | None = None,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[RateLimitCheckResponse]:
    """Check if request would be allowed under rate limits."""
    key = f"{tenant_id}:{site}"
    if credential_id:
        key = f"{tenant_id}:{credential_id}"

    result = await rate_limiter.check_rate_limit(key)

    return APIResponse(
        data=RateLimitCheckResponse(
            allowed=result.allowed,
            wait_seconds=result.wait_seconds,
            remaining=result.remaining,
        )
    )
