"""
SEO Platform — Authentication & Identity
=========================================
Internal-use only. Always returns a mock admin user.
No external auth provider (Clerk/Auth0) is integrated.
"""

from uuid import UUID

from pydantic import BaseModel

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class CurrentUser(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: str = "admin"


async def get_current_user() -> CurrentUser:
    """Internal-only auth — always returns a mock admin user."""
    return CurrentUser(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
        email="admin@buildit.local",
        role="admin",
    )
