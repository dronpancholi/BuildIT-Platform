"""
SEO Platform — Tenant Endpoints
==================================
Tenant management API (admin-only).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse

router = APIRouter()


class CreateTenantRequest(BaseModel):
    slug: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=255)
    plan: str = Field(default="starter")


class TenantResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    plan: str
    is_suspended: bool = False


@router.post("", response_model=APIResponse[TenantResponse], status_code=201)
async def create_tenant(request: CreateTenantRequest) -> APIResponse[TenantResponse]:
    """Create a new tenant (super_admin only)."""
    from seo_platform.core.database import get_session
    from seo_platform.models.tenant import Tenant, TenantPlan

    async with get_session() as session:
        tenant = Tenant(
            slug=request.slug,
            name=request.name,
            plan=TenantPlan(request.plan),
        )
        session.add(tenant)
        await session.flush()
        await session.refresh(tenant)

        return APIResponse(
            data=TenantResponse(
                id=tenant.id,
                slug=tenant.slug,
                name=tenant.name,
                plan=tenant.plan.value,
                is_suspended=tenant.is_suspended,
            )
        )


@router.get("/{tenant_id}", response_model=APIResponse[TenantResponse])
async def get_tenant(tenant_id: UUID) -> APIResponse[TenantResponse]:
    """Get tenant by ID."""
    from sqlalchemy import select

    from seo_platform.core.database import get_session
    from seo_platform.models.tenant import Tenant

    async with get_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        return APIResponse(
            data=TenantResponse(
                id=tenant.id,
                slug=tenant.slug,
                name=tenant.name,
                plan=tenant.plan.value,
                is_suspended=tenant.is_suspended,
            )
        )
