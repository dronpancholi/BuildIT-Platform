"""
SEO Platform — Authentication & Identity (Phase 2.5.1)
=======================================================
JWT-based authentication using Clerk as the identity provider.

Operating modes:

1. PRODUCTION (APP_ENV=production):
   - REQUIRES CLERK_JWKS_URL, CLERK_PUBLISHABLE_KEY, CLERK_AUDIENCE.
   - Startup fails if any of these is missing.
   - Every request requires `Authorization: Bearer <jwt>`.
   - The JWT is verified against the Clerk JWKS endpoint.
   - The Clerk user_id (sub claim) is mapped to an internal user row.
   - The tenant_id and role come from the internal user row, NOT the JWT.
   - X-User-* headers are NOT trusted.

2. STAGING (APP_ENV=staging):
   - Same as production. No bypass.

3. DEVELOPMENT (APP_ENV=development):
   - If CLERK_JWKS_URL is configured, behaves like production.
   - If CLERK_JWKS_URL is not configured, accepts unsigned dev tokens
     of the form `dev:<user_id>:<tenant_id>` (gated by DEV_AUTH_BYPASS=true).
   - This is the ONLY allowed dev bypass and is explicit about it.

Session/cookie management is delegated to Clerk (handled in the frontend).
The backend is stateless: every request carries its own verified identity.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, Query, Request, status
from jose import jwt as jose_jwt
from jose.exceptions import JWTError
from pydantic import BaseModel

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Dev-only fallback identity (used ONLY when DEV_AUTH_BYPASS=true and APP_ENV=development)
# ---------------------------------------------------------------------------
_DEV_FALLBACK_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
_DEV_FALLBACK_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
_DEV_FALLBACK_EMAIL = "dev@buildit.local"


# ---------------------------------------------------------------------------
# CurrentUser model
# ---------------------------------------------------------------------------
class CurrentUser(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: str = "viewer"
    clerk_user_id: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# DB role → RBAC role mapping (preserved from prior work)
# ---------------------------------------------------------------------------
_DB_TO_RBAC_ROLE = {
    "super_admin": "super_admin",
    "tenant_admin": "admin",
    "manager": "manager",
    "seo_analyst": "operator",
    "outreach_specialist": "operator",
    "report_analyst": "viewer",
    "client": "viewer",
}


def _map_db_role_to_rbac(db_role: str | None) -> str:
    if not db_role:
        return "viewer"
    return _DB_TO_RBAC_ROLE.get(db_role, "viewer")


# ---------------------------------------------------------------------------
# Clerk JWKS cache (1 hour TTL, refresh on key not found)
# ---------------------------------------------------------------------------
_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


async def _get_jwks_keys(jwks_url: str) -> list[dict[str, Any]]:
    """Fetch and cache the JWKS keys from Clerk."""
    now = time.time()
    if _JWKS_CACHE["keys"] is not None and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        data = resp.json()
    _JWKS_CACHE["keys"] = data.get("keys", [])
    _JWKS_CACHE["fetched_at"] = now
    return _JWKS_CACHE["keys"]


async def _verify_clerk_jwt(token: str) -> dict[str, Any]:
    """
    Verify a Clerk JWT against the configured JWKS endpoint.

    Returns the decoded claims dict on success.
    Raises HTTPException(401) on any verification failure.
    """
    from seo_platform.config import get_settings
    settings = get_settings()
    auth = settings.auth

    if not auth.jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth provider not configured (AUTH_JWKS_URL missing)",
        )

    try:
        keys = await _get_jwks_keys(auth.jwks_url)
        unverified_header = jose_jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="JWT missing 'kid' header")

        # Find the matching key
        matching_key = None
        for k in keys:
            if k.get("kid") == kid:
                matching_key = k
                break

        if matching_key is None:
            # Refresh cache and try once more
            _JWKS_CACHE["keys"] = None
            keys = await _get_jwks_keys(auth.jwks_url)
            for k in keys:
                if k.get("kid") == kid:
                    matching_key = k
                    break

        if matching_key is None:
            raise HTTPException(status_code=401, detail="JWT signing key not found in JWKS")

        claims = jose_jwt.decode(
            token,
            matching_key,
            algorithms=[matching_key.get("alg", "RS256")],
            audience=auth.audience or None,
            issuer=auth.issuer_url or None,
            options={"verify_aud": bool(auth.audience), "verify_iss": bool(auth.issuer_url)},
        )
        return claims
    except HTTPException:
        raise
    except JWTError as e:
        logger.warning("jwt_verification_failed", error=str(e))
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        logger.error("jwt_verification_error", error=str(e))
        raise HTTPException(status_code=401, detail=f"Token verification failed")


async def _resolve_user_from_clerk_token(claims: dict[str, Any]) -> CurrentUser:
    """
    Map a verified Clerk JWT to an internal CurrentUser.

    The Clerk `sub` (subject) claim is the Clerk user_id (e.g. "user_abc123").
    We look up the internal user row by `clerk_user_id` and read the
    internal tenant_id and role from there. This is the ONLY trust anchor.
    """
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="JWT missing 'sub' claim")

    try:
        async with get_session() as session:
            result = await session.execute(
                text(
                    "SELECT id, tenant_id, email, role::text, is_active "
                    "FROM users WHERE external_id = :cuid LIMIT 1"
                ),
                {"cuid": clerk_user_id},
            )
            row = result.first()
            if row is None:
                # Fallback: try by email (for users created via email match)
                email = claims.get("email") or claims.get("primary_email") or ""
                if not email:
                    raise HTTPException(
                        status_code=403,
                        detail="No internal user found for this Clerk identity. Contact your administrator.",
                    )
                result = await session.execute(
                    text(
                        "SELECT id, tenant_id, email, role::text, is_active "
                        "FROM users WHERE lower(email) = :email LIMIT 1"
                    ),
                    {"email": email.lower()},
                )
                row = result.first()
                if row is None:
                    raise HTTPException(
                        status_code=403,
                        detail="No internal user found for this Clerk identity. Contact your administrator.",
                    )

            user_id, tenant_id, db_email, db_role, is_active = row
            if not is_active:
                raise HTTPException(status_code=403, detail="User is inactive")

            return CurrentUser(
                id=user_id,
                tenant_id=tenant_id,
                email=db_email or email,
                role=_map_db_role_to_rbac(db_role),
                clerk_user_id=clerk_user_id,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("clerk_user_resolution_failed", error=str(e), clerk_user_id=clerk_user_id)
        raise HTTPException(status_code=401, detail="User resolution failed")


def _parse_dev_token(authorization: str) -> CurrentUser:
    """
    Parse a dev token of the form `dev:<user_id>:<tenant_id>[:role][:email]`.
    Used ONLY when DEV_AUTH_BYPASS=true AND APP_ENV=development.
    Refuses in any other environment.
    """
    parts = authorization.split(":")
    if len(parts) < 3 or parts[0] != "dev":
        raise HTTPException(status_code=401, detail="Invalid dev token format")
    try:
        uid = UUID(parts[1])
        tid = UUID(parts[2])
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid dev token UUID: {e}")
    role = parts[3] if len(parts) > 3 else "admin"
    # The "email" portion may contain '@' and ':' chars; reassemble.
    if len(parts) >= 5:
        email = ":".join(parts[4:])
    else:
        email = f"dev-{uid}@buildit.local"
    return CurrentUser(
        id=uid,
        tenant_id=tid,
        email=email,
        role=role,
        clerk_user_id=f"dev-clerk-{uid}",  # Synthesized so the user lookup by external_id works
    )


async def _resolve_user_from_dev_token(token: str) -> CurrentUser:
    """
    Resolve a dev token to a CurrentUser by looking up the user row in the
    database. The dev token's <uuid> is the internal users.id, so this mirrors
    the production path (DB lookup, mapped role, is_active check). This avoids
    trusting the role string in the dev token itself.
    """
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    parsed = _parse_dev_token(token)
    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, tenant_id, email, role::text, is_active, external_id "
                "FROM users WHERE id = :uid LIMIT 1"
            ),
            {"uid": str(parsed.id)},
        )
        row = result.first()
        if row is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"No internal user with id={parsed.id}. Dev tokens "
                    "must reference an existing users.id."
                ),
            )
        user_id, tenant_id, db_email, db_role, is_active, external_id = row
        if not is_active:
            raise HTTPException(status_code=403, detail="User is inactive")
        if str(tenant_id) != str(parsed.tenant_id):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Dev token tenant_id={parsed.tenant_id} does not match "
                    f"DB tenant_id={tenant_id} for user {user_id}."
                ),
            )
        return CurrentUser(
            id=user_id,
            tenant_id=tenant_id,
            email=db_email or parsed.email,
            role=_map_db_role_to_rbac(db_role),
            clerk_user_id=external_id or parsed.clerk_user_id,
        )


# ---------------------------------------------------------------------------
# FastAPI dependency: get_current_user
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> CurrentUser:
    """
    Resolve the current authenticated user from `Authorization: Bearer <jwt>`.

    PRODUCTION (APP_ENV=production OR AUTH_JWKS_URL set):
        - Verifies the JWT against Clerk JWKS.
        - Maps the Clerk user to an internal user.
        - Returns 401 if any step fails.
        - The startup check refuses to launch without CLERK_JWKS_URL in production.

    DEV (APP_ENV=development AND DEV_AUTH_BYPASS=true AND no JWKS):
        - Accepts `Authorization: Bearer dev:<user_id>:<tenant_id>[:role]`.
        - This is the ONLY allowed bypass; gated by env vars.
    """
    from seo_platform.config import get_settings
    settings = get_settings()

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Use 'Authorization: Bearer <jwt>'",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header must use Bearer scheme",
        )

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty Bearer token")

    # Decide mode
    jwks_url = settings.auth.jwks_url

    if jwks_url:
        # Production-grade path: real Clerk verification
        claims = await _verify_clerk_jwt(token)
        user = await _resolve_user_from_clerk_token(claims)
    elif settings.is_development and settings.dev_auth_bypass:
        # Dev-only path: accept "dev:<uuid>:<uuid>[:role]"
        # The dev token's <uuid> IS the internal users.id; we look up the
        # DB row and use its (mapped) role, mirroring the production path.
        user = await _resolve_user_from_dev_token(token)
    else:
        # Neither production path nor dev bypass: refuse
        raise HTTPException(
            status_code=503,
            detail="Auth provider not configured. Set AUTH_JWKS_URL or enable DEV_AUTH_BYPASS in development.",
        )

    # Expose identity to downstream middleware
    request.state.tenant_id = str(user.tenant_id)
    request.state.user_id = str(user.id)
    request.state.role = user.role
    request.state.clerk_user_id = user.clerk_user_id
    return user


# ---------------------------------------------------------------------------
# Tenant validation (unchanged behavior, but now driven by JWT)
# ---------------------------------------------------------------------------
async def get_validated_tenant_id(
    request: Request,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    user: CurrentUser = Depends(get_current_user),
) -> UUID:
    """
    Validate that the requested tenant_id matches the authenticated user's tenant.
    Prevents cross-tenant access via query parameter manipulation.
    """
    if tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: tenant_id does not match authenticated user",
        )
    return tenant_id


async def validate_tenant_id(
    tenant_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> UUID:
    """
    Validate a tenant_id from request body against the authenticated user's tenant.
    """
    if tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: tenant_id does not match authenticated user",
        )
    return tenant_id
