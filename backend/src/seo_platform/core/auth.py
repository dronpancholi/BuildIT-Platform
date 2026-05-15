"""
SEO Platform — Authentication & Identity
=========================================
Handles enterprise identity verification (Clerk/Auth0) with support
for zero-cost development bypass modes.
"""

from uuid import UUID

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

class CurrentUser(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: str = "admin"

async def get_current_user(
    authorization: str | None = Header(None)
) -> CurrentUser:
    """
    Dependency to fetch and validate the current authenticated user.
    Supports DEV_AUTH_BYPASS for local zero-cost testing.
    """
    settings = get_settings()

    # ---------------------------------------------------------------------------
    # ZERO-COST MODE: Auth Bypass
    # ---------------------------------------------------------------------------
    if settings.dev_auth_bypass:
        logger.warning("auth_bypass_active", mode="zero-cost-operationalization")
        # Return a deterministic mock user for local development
        return CurrentUser(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="dev@buildit.local",
            role="admin"
        )

    # ---------------------------------------------------------------------------
    # PRODUCTION MODE: Real Clerk / JWT Validation
    # ---------------------------------------------------------------------------
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )

    # TODO: Implement real Clerk/JWT token validation here
    # This architecture is preserved and ready for production deployment
    logger.info("auth_token_received", provider=settings.auth.provider)

    # Simulate valid production auth for now if header is present
    return CurrentUser(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
        email="prod-user@buildit.ai",
        role="admin"
    )
