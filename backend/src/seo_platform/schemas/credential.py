"""
SEO Platform — Credential Vault Schemas
========================================
Pydantic models for credential management API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class CredentialCreateRequest(BaseModel):
    """Request to add a new credential."""

    site_slug: str = Field(..., min_length=1, max_length=100)
    site_name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)
    recovery_email: str | None = None
    recovery_phone: str | None = None
    notes: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class CredentialUpdateRequest(BaseModel):
    """Request to update a credential."""

    email: str | None = None
    password: str | None = None
    recovery_email: str | None = None
    recovery_phone: str | None = None
    notes: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v and v not in ("active", "suspended", "banned", "locked", "expired"):
            raise ValueError("Invalid status")
        return v


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------
class CredentialResponse(BaseModel):
    """Response schema for a credential."""

    id: UUID
    tenant_id: UUID
    site_slug: str
    site_name: str
    email: str
    status: str
    health_score: int
    use_count: int
    failure_count: int
    last_used_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_failure_reason: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class VaultSummaryResponse(BaseModel):
    """Summary stats for vault dashboard."""

    total: int
    active: int
    locked: int
    banned: int
    suspended: int
    avg_health: int


class CredentialListResponse(BaseModel):
    """List of credentials with summary."""

    credentials: list[CredentialResponse]
    summary: VaultSummaryResponse


class SiteHealthResponse(BaseModel):
    """Health summary for a site's credential pool."""

    site_slug: str
    total: int
    active: int
    locked: int
    banned: int
    avg_health: int


class CredentialTestResponse(BaseModel):
    """Response from credential test."""

    success: bool
    credential_id: UUID
    message: str
    response_time_ms: float = 0


class CredentialAuditLogResponse(BaseModel):
    """Audit log entry."""

    id: UUID
    credential_id: UUID | None = None
    action: str
    site_slug: str | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
