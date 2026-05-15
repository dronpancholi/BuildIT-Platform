"""
SEO Platform — Shared Pydantic Schemas
=========================================
Common request/response schemas used across service boundaries.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


# ---------------------------------------------------------------------------
# Standard API Response Envelope
# ---------------------------------------------------------------------------
class APIResponse(BaseModel, Generic[DataT]):
    """Standard API response wrapper for consistency across all endpoints."""
    success: bool = True
    data: DataT | None = None
    error: ErrorDetail | None = None
    meta: ResponseMeta | None = None


class ErrorDetail(BaseModel):
    """Structured error payload for API error responses."""
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class ResponseMeta(BaseModel):
    """Pagination and metadata for list responses."""
    total: int | None = None
    offset: int = 0
    limit: int = 50
    has_more: bool = False


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints."""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)
    order_by: str | None = None


# ---------------------------------------------------------------------------
# Tenant Context
# ---------------------------------------------------------------------------
class TenantContext(BaseModel):
    """Tenant context extracted from auth token — available in every request."""
    tenant_id: UUID
    tenant_slug: str
    tenant_plan: str


class UserContext(BaseModel):
    """Authenticated user context — available in every request."""
    user_id: UUID
    tenant_id: UUID
    email: str
    name: str
    role: str
    permissions: list[str] = Field(default_factory=list)


class RequestContext(BaseModel):
    """Full request context combining tenant + user + trace."""
    tenant: TenantContext
    user: UserContext
    trace_id: str | None = None
    request_id: str | None = None


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
class HealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    status: HealthStatus
    version: str
    environment: str
    components: list[ComponentHealth] = Field(default_factory=list)
    timestamp: datetime


# ---------------------------------------------------------------------------
# Common Domain Schemas
# ---------------------------------------------------------------------------
class GeoTarget(BaseModel):
    """Geographic targeting configuration."""
    country: str
    region: str | None = None
    city: str | None = None


class ConfidenceScore(BaseModel):
    """Confidence assessment for AI-generated outputs."""
    score: float = Field(..., ge=0.0, le=1.0)
    requires_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)

    @property
    def tier(self) -> str:
        if self.score >= 0.90:
            return "auto_proceed"
        elif self.score >= 0.75:
            return "flag_and_proceed"
        else:
            return "halt_for_review"
