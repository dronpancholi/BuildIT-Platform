"""
SEO Platform — Identity & Onboarding Endpoints (Phase 2.5.1)
=============================================================
Provides:

- GET  /api/v1/me                          — current user (from verified JWT)
- POST /api/v1/tenants/onboard             — create a clean tenant + first user
                                              (Clerk user_id from Authorization)
- POST /api/v1/users/invite                — invite a teammate
- POST /api/v1/users/{user_id}/activate    — activate a previously-inactive user
- POST /api/v1/users/{user_id}/deactivate  — deactivate a user
- PUT  /api/v1/users/{user_id}/role        — assign a new role

These endpoints are the foundation for real customer onboarding. They are
auth-required, tenant-scoped, and produce real DB rows (no synthetic data).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.rbac import RequirePermission
from seo_platform.schemas import APIResponse
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class MeResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: str
    clerk_user_id: str | None
    is_active: bool
    permissions: list[str]


class OnboardTenantRequest(BaseModel):
    tenant_name: str = Field(..., min_length=1, max_length=255)
    tenant_slug: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: Literal["starter", "professional", "enterprise"] = "starter"
    clerk_user_id_override: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Optional. When the calling Clerk user is already bound to a "
            "different tenant, the caller may supply a unique Clerk user ID "
            "for the new tenant's first tenant_admin. The original Clerk ID "
            "is preserved on the original tenant. This is a Phase 2.5.1 "
            "workaround pending a proper tenant_memberships table."
        ),
    )


class OnboardTenantResponse(BaseModel):
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str
    user_id: UUID
    email: str
    role: str
    external_id: str


class InviteUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: Literal["tenant_admin", "manager", "seo_analyst", "outreach_specialist", "report_analyst", "client"] = "seo_analyst"


class InviteUserResponse(BaseModel):
    user_id: UUID
    email: str
    role: str
    invite_token: str  # The operator can hand this to the new user out-of-band
    message: str


class UserStatusResponse(BaseModel):
    user_id: UUID
    is_active: bool


class UserRoleUpdateRequest(BaseModel):
    role: Literal["tenant_admin", "manager", "seo_analyst", "outreach_specialist", "report_analyst", "client"]


class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    name: str
    role: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# /me endpoint
# ---------------------------------------------------------------------------
@router.get("/me", response_model=APIResponse[MeResponse])
async def get_me(
    user: CurrentUser = Depends(get_current_user),
    _auth: None = Depends(RequirePermission("system:read")),
) -> APIResponse[MeResponse]:
    """
    Return the currently authenticated user, derived from the verified
    Clerk JWT. No X-User-* headers are trusted.
    """
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, tenant_id, email, role::text, is_active, permissions, "
                "       last_login_at "
                "FROM users WHERE id = :uid LIMIT 1"
            ),
            {"uid": str(user.id)},
        )
        row = result.first()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        uid, tid, email, db_role, is_active, perms, last_login = row

        # Update last_login_at (best-effort)
        try:
            await session.execute(
                text("UPDATE users SET last_login_at = now() WHERE id = :uid"),
                {"uid": str(uid)},
            )
            await session.commit()
        except Exception:
            pass

        return APIResponse(
            data=MeResponse(
                id=uid,
                tenant_id=tid,
                email=email,
                role=user.role,
                clerk_user_id=user.clerk_user_id,
                is_active=is_active,
                permissions=list(perms or []),
            )
        )


# ---------------------------------------------------------------------------
# Tenant onboarding (clean state)
# ---------------------------------------------------------------------------
@router.post("/onboard", response_model=APIResponse[OnboardTenantResponse], status_code=201)
async def onboard_tenant(
    request: OnboardTenantRequest,
    user: CurrentUser = Depends(get_current_user),
    _auth: None = Depends(RequirePermission("system:write")),
) -> APIResponse[OnboardTenantResponse]:
    """
    Onboard a brand new tenant with the calling user as the first
    tenant_admin. This is the clean path for real customer onboarding:

    1. Create a new tenant (0 clients, 0 campaigns, 0 prospects).
    2. Bind the calling Clerk user to the new tenant as tenant_admin.

    The tenant starts EMPTY. No seed data, no Faker, no synthetic anything.
    """
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        # Check slug uniqueness
        existing = (await session.execute(
            text("SELECT 1 FROM tenants WHERE slug = :slug"),
            {"slug": request.tenant_slug},
        )).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tenant slug '{request.tenant_slug}' is already taken",
            )

        # Create tenant
        new_tenant_id = uuid4()
        await session.execute(
            text(
                "INSERT INTO tenants (id, slug, name, plan, created_at, updated_at) "
                "VALUES (:id, :slug, :name, :plan, now(), now())"
            ),
            {
                "id": str(new_tenant_id),
                "slug": request.tenant_slug,
                "name": request.tenant_name,
                "plan": request.plan,
            },
        )

        # Bind the calling Clerk user to the new tenant as tenant_admin.
        # Phase 2.5.1 workaround: if the calling Clerk user is already bound
        # to another tenant, the caller must supply `clerk_user_id_override`
        # so the new tenant's tenant_admin row has a globally-unique
        # external_id. The original Clerk ID remains on the original tenant.
        # Pending: a proper tenant_memberships table for many-to-many.
        original_clerk_id = user.clerk_user_id
        if not original_clerk_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot onboard without a verified Clerk identity (sub claim missing).",
            )

        clerk_id = request.clerk_user_id_override or original_clerk_id

        # Verify external_id is globally unique (the schema enforces it).
        clash = (await session.execute(
            text("SELECT id FROM users WHERE external_id = :cuid LIMIT 1"),
            {"cuid": clerk_id},
        )).first()
        if clash and request.clerk_user_id_override is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Clerk user '{clerk_id}' is already bound to a tenant. "
                    "Supply clerk_user_id_override to bind a distinct Clerk "
                    "identity as this new tenant's first tenant_admin."
                ),
            )
        if clash and str(clash[0]) == str(user.id):
            # Edge case: same Clerk ID belongs to the calling user. That's fine.
            pass

        new_user_id = uuid4()
        try:
            await session.execute(
                text(
                    "INSERT INTO users (id, tenant_id, external_id, email, name, role, is_active, "
                    "                    permissions, created_at, updated_at) "
                    "VALUES (:id, :tid, :cuid, :email, :name, 'tenant_admin', true, "
                    "        '[]'::jsonb, now(), now())"
                ),
                {
                    "id": str(new_user_id),
                    "tid": str(new_tenant_id),
                    "cuid": clerk_id,
                    "email": user.email,
                    "name": user.email.split("@")[0] or "Owner",
                },
            )
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"external_id '{clerk_id}' already taken: {e}",
            )
        user_id = new_user_id

        await session.commit()

        logger.info(
            "tenant_onboarded",
            tenant_id=str(new_tenant_id),
            user_id=str(user_id),
            slug=request.tenant_slug,
            used_override=bool(request.clerk_user_id_override),
        )

        return APIResponse(
            data=OnboardTenantResponse(
                tenant_id=new_tenant_id,
                tenant_slug=request.tenant_slug,
                tenant_name=request.tenant_name,
                user_id=user_id,
                email=user.email,
                role="tenant_admin",
                external_id=clerk_id,
            )
        )


# ---------------------------------------------------------------------------
# User invite / activate / deactivate / role
# ---------------------------------------------------------------------------
@router.post("/users/invite", response_model=APIResponse[InviteUserResponse], status_code=201)
async def invite_user(
    request: InviteUserRequest,
    user: CurrentUser = Depends(get_current_user),
    _auth: None = Depends(RequirePermission("users:write")),
) -> APIResponse[InviteUserResponse]:
    """
    Invite a teammate by email. The invite creates a placeholder user row
    bound to the calling user's tenant. The new user must sign up via Clerk
    with the same email for the link to activate; the invite_token is
    returned for the operator to communicate out-of-band.
    """
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    invite_token = secrets.token_urlsafe(24)
    placeholder_external_id = f"pending-{invite_token}"

    async with get_session() as session:
        # Check for existing user with same email in this tenant
        existing = (await session.execute(
            text(
                "SELECT id FROM users WHERE tenant_id = :tid AND lower(email) = :email LIMIT 1"
            ),
            {"tid": str(user.tenant_id), "email": request.email.lower()},
        )).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {request.email} already exists in this tenant",
            )

        new_user_id = uuid4()
        await session.execute(
            text(
                "INSERT INTO users (id, tenant_id, external_id, email, name, role, is_active, "
                "                    permissions, created_at, updated_at) "
                "VALUES (:id, :tid, :cuid, :email, :name, :role, false, "
                "        '[]'::jsonb, now(), now())"
            ),
            {
                "id": str(new_user_id),
                "tid": str(user.tenant_id),
                "cuid": placeholder_external_id,
                "email": request.email,
                "name": request.name,
                "role": request.role,
            },
        )
        await session.commit()

        return APIResponse(
            data=InviteUserResponse(
                user_id=new_user_id,
                email=request.email,
                role=request.role,
                invite_token=invite_token,
                message=(
                    "User created in pending state. They must sign up via Clerk with this "
                    "exact email. The placeholder external_id will be updated to their Clerk "
                    "user_id upon first login."
                ),
            )
        )


@router.post("/users/{user_id}/activate", response_model=APIResponse[UserStatusResponse])
async def activate_user(
    user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    _auth: None = Depends(RequirePermission("users:write")),
) -> APIResponse[UserStatusResponse]:
    """Activate a previously-deactivated user (admin only, same tenant)."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text("UPDATE users SET is_active = true, updated_at = now() "
                 "WHERE id = :uid AND tenant_id = :tid RETURNING id"),
            {"uid": str(user_id), "tid": str(user.tenant_id)},
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found in this tenant")
        await session.commit()
        return APIResponse(data=UserStatusResponse(user_id=user_id, is_active=True))


@router.post("/users/{user_id}/deactivate", response_model=APIResponse[UserStatusResponse])
async def deactivate_user(
    user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    _auth: None = Depends(RequirePermission("users:write")),
) -> APIResponse[UserStatusResponse]:
    """Deactivate a user (admin only, same tenant). Cannot deactivate yourself."""
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text("UPDATE users SET is_active = false, updated_at = now() "
                 "WHERE id = :uid AND tenant_id = :tid RETURNING id"),
            {"uid": str(user_id), "tid": str(user.tenant_id)},
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found in this tenant")
        await session.commit()
        return APIResponse(data=UserStatusResponse(user_id=user_id, is_active=False))


@router.put("/users/{user_id}/role", response_model=APIResponse[UserResponse])
async def update_user_role(
    user_id: UUID,
    request: UserRoleUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    _auth: None = Depends(RequirePermission("users:write")),
) -> APIResponse[UserResponse]:
    """Assign a new role to a user (admin only, same tenant)."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text("UPDATE users SET role = :role, updated_at = now() "
                 "WHERE id = :uid AND tenant_id = :tid "
                 "RETURNING id, tenant_id, email, name, role::text, is_active, "
                 "          last_login_at, created_at"),
            {"uid": str(user_id), "tid": str(user.tenant_id), "role": request.role},
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found in this tenant")
        await session.commit()
        uid, tid, email, name, role, is_active, last_login, created_at = row
        return APIResponse(
            data=UserResponse(
                id=uid,
                tenant_id=tid,
                email=email,
                name=name,
                role=role,
                is_active=is_active,
                last_login_at=last_login,
                created_at=created_at,
            )
        )


@router.get("/users", response_model=APIResponse[list[UserResponse]])
async def list_users(
    user: CurrentUser = Depends(get_current_user),
    _auth: None = Depends(RequirePermission("users:read")),
) -> APIResponse[list[UserResponse]]:
    """List all users in the calling user's tenant."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, tenant_id, email, name, role::text, is_active, "
                "       last_login_at, created_at "
                "FROM users WHERE tenant_id = :tid "
                "ORDER BY created_at DESC"
            ),
            {"tid": str(user.tenant_id)},
        )
        rows = result.all()
        return APIResponse(
            data=[
                UserResponse(
                    id=r[0],
                    tenant_id=r[1],
                    email=r[2],
                    name=r[3],
                    role=r[4],
                    is_active=r[5],
                    last_login_at=r[6],
                    created_at=r[7],
                )
                for r in rows
            ]
        )


# ---------------------------------------------------------------------------
# Dev-only: mint a Bearer dev token for an existing user
# ---------------------------------------------------------------------------
class DevLoginRequest(BaseModel):
    """Body for the dev-only login endpoint.

    One of `email` or `user_id` must be provided. If neither is provided,
    the first active super_admin in the default tenant is returned.
    """
    email: str | None = None
    user_id: UUID | None = None
    tenant_id: UUID | None = None


class DevLoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user_id: UUID
    tenant_id: UUID
    email: str
    role: str


@router.post("/dev/login", response_model=APIResponse[DevLoginResponse])
async def dev_login(request: DevLoginRequest) -> APIResponse[DevLoginResponse]:
    """
    DEV-ONLY: mint a Bearer token of the form
    `dev:<users.id>:<tenant_id>:<role>:<email>` for an existing user.

    Gated by:
        APP_ENV=development AND DEV_AUTH_BYPASS=true.

    Refuses with 403 in any other environment (checked via the auth service
    settings). This endpoint exists so the local Next.js frontend can obtain
    a real Bearer token without Clerk, since Clerk is not configured in dev.

    The token, when sent as `Authorization: Bearer <token>`, is resolved by
    `_resolve_user_from_dev_token` (auth.py) which re-looks-up the user row
    in the database — so the dev token does NOT itself grant access; the
    row must exist and be active.
    """
    from seo_platform.config import get_settings
    settings = get_settings()

    if not (settings.is_development and settings.dev_auth_bypass):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Dev login is disabled. Set APP_ENV=development AND "
                "DEV_AUTH_BYPASS=true to enable."
            ),
        )

    from seo_platform.core.database import get_session
    from sqlalchemy import text

    where_clauses: list[str] = []
    params: dict[str, str] = {}
    if request.user_id:
        where_clauses.append("id = :uid")
        params["uid"] = str(request.user_id)
    if request.email:
        where_clauses.append("email = :email")
        params["email"] = request.email
    if request.tenant_id:
        where_clauses.append("tenant_id = :tid")
        params["tid"] = str(request.tenant_id)
    where_clauses.append("is_active = true")

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    async with get_session() as session:
        result = await session.execute(
            text(
                f"SELECT id, tenant_id, email, role::text "
                f"FROM users WHERE {where_sql} "
                f"ORDER BY (role = 'super_admin') DESC, created_at ASC "
                f"LIMIT 1"
            ),
            params,
        )
        row = result.first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No active user matched (email={request.email}, "
                    f"user_id={request.user_id}, "
                    f"tenant_id={request.tenant_id})."
                ),
            )
        uid, tid, email, db_role = row

    token = f"dev:{uid}:{tid}:{db_role}:{email}"
    return APIResponse(
        data=DevLoginResponse(
            access_token=token,
            token_type="Bearer",
            user_id=uid,
            tenant_id=tid,
            email=email,
            role=db_role,
        )
    )
