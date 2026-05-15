"""
SEO Platform — Exception Hierarchy
====================================
Structured exception hierarchy for enterprise-grade error handling.

Design principles:
- Every exception carries structured context (not just a message string)
- Exceptions map to HTTP status codes at the API boundary
- Non-retryable errors are explicitly marked (Temporal integration)
- All exceptions are serializable for audit logging
"""

from __future__ import annotations

from typing import Any
from uuid import UUID


class PlatformError(Exception):
    """
    Base exception for all platform errors.

    Every exception in the platform extends this class, ensuring:
    - Structured error codes for API responses
    - Machine-readable context for observability
    - Consistent serialization for audit logs
    """

    error_code: str = "PLATFORM_ERROR"
    http_status: int = 500
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        if error_code:
            self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API responses and audit logs."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
        }


# ---------------------------------------------------------------------------
# Authentication & Authorization
# ---------------------------------------------------------------------------
class AuthenticationError(PlatformError):
    """Invalid or missing credentials."""

    error_code = "AUTHENTICATION_FAILED"
    http_status = 401


class AuthorizationError(PlatformError):
    """Insufficient permissions for the requested operation."""

    error_code = "AUTHORIZATION_DENIED"
    http_status = 403


class TokenExpiredError(AuthenticationError):
    """JWT access token has expired."""

    error_code = "TOKEN_EXPIRED"


# ---------------------------------------------------------------------------
# Tenant & Multi-Tenancy
# ---------------------------------------------------------------------------
class TenantError(PlatformError):
    """Base for tenant-related errors."""

    error_code = "TENANT_ERROR"


class TenantNotFoundError(TenantError):
    """Tenant does not exist."""

    error_code = "TENANT_NOT_FOUND"
    http_status = 404


class TenantSuspendedError(TenantError):
    """Tenant account is suspended. Non-retryable — human must resolve."""

    error_code = "TENANT_SUSPENDED"
    http_status = 403
    retryable = False


class TenantQuotaExceededError(TenantError):
    """Tenant has exceeded a resource quota."""

    error_code = "TENANT_QUOTA_EXCEEDED"
    http_status = 429
    retryable = True  # May succeed after quota reset

    def __init__(
        self,
        tenant_id: UUID,
        resource: str,
        limit: int,
        current_usage: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            f"Tenant {tenant_id} exceeded {resource} quota: limit={limit}",
            details={
                "tenant_id": str(tenant_id),
                "resource": resource,
                "limit": limit,
                "current_usage": current_usage,
            },
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class ValidationError(PlatformError):
    """Input validation failure. Non-retryable — client must fix input."""

    error_code = "VALIDATION_ERROR"
    http_status = 422
    retryable = False


class SchemaValidationError(ValidationError):
    """Pydantic schema validation failure (typically from LLM output)."""

    error_code = "SCHEMA_VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# Resource / Entity
# ---------------------------------------------------------------------------
class EntityNotFoundError(PlatformError):
    """Requested entity does not exist."""

    error_code = "ENTITY_NOT_FOUND"
    http_status = 404

    def __init__(self, entity_type: str, entity_id: str | UUID, **kwargs: Any) -> None:
        super().__init__(
            f"{entity_type} not found: {entity_id}",
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
            **kwargs,
        )


class DuplicateEntityError(PlatformError):
    """Attempted to create an entity that already exists."""

    error_code = "DUPLICATE_ENTITY"
    http_status = 409
    retryable = False


class DuplicateOperationError(PlatformError):
    """Idempotency violation — operation already executed."""

    error_code = "DUPLICATE_OPERATION"
    http_status = 409
    retryable = False


# ---------------------------------------------------------------------------
# Workflow & Orchestration
# ---------------------------------------------------------------------------
class WorkflowError(PlatformError):
    """Base for workflow execution errors."""

    error_code = "WORKFLOW_ERROR"


class WorkflowBlockedError(WorkflowError):
    """Workflow blocked by rules engine or kill switch."""

    error_code = "WORKFLOW_BLOCKED"
    http_status = 403
    retryable = False


class ApprovalRequiredError(WorkflowError):
    """Workflow paused — awaiting human approval."""

    error_code = "APPROVAL_REQUIRED"
    http_status = 202  # Accepted, pending approval


class ApprovalRejectedError(WorkflowError):
    """Human reviewer rejected the approval request."""

    error_code = "APPROVAL_REJECTED"
    http_status = 403
    retryable = False


# ---------------------------------------------------------------------------
# AI / LLM
# ---------------------------------------------------------------------------
class LLMError(PlatformError):
    """Base for LLM inference errors."""

    error_code = "LLM_ERROR"
    retryable = True


class LLMTimeoutError(LLMError):
    """LLM inference timed out."""

    error_code = "LLM_TIMEOUT"
    retryable = True


class LLMRateLimitError(LLMError):
    """LLM provider rate limit hit."""

    error_code = "LLM_RATE_LIMITED"
    http_status = 429
    retryable = True


class OutputSchemaError(LLMError):
    """LLM output failed schema validation after repair attempt."""

    error_code = "LLM_OUTPUT_SCHEMA_ERROR"
    retryable = False  # Retrying same prompt won't fix schema issues


class LowConfidenceError(LLMError):
    """LLM output confidence below threshold. Not a transient failure."""

    error_code = "LLM_LOW_CONFIDENCE"
    retryable = False


class PromptValidationError(LLMError):
    """Prompt template validation failed before inference."""

    error_code = "PROMPT_VALIDATION_ERROR"
    retryable = False


# ---------------------------------------------------------------------------
# External Services
# ---------------------------------------------------------------------------
class ExternalServiceError(PlatformError):
    """External API call failed."""

    error_code = "EXTERNAL_SERVICE_ERROR"
    retryable = True

    def __init__(self, service_name: str, message: str, **kwargs: Any) -> None:
        super().__init__(
            f"[{service_name}] {message}",
            details={"service": service_name},
            **kwargs,
        )


class CircuitOpenError(ExternalServiceError):
    """Circuit breaker is open for this service."""

    error_code = "CIRCUIT_OPEN"
    retryable = True  # Will succeed after circuit recovery


class RateLimitedError(PlatformError):
    """Rate limit exceeded."""

    error_code = "RATE_LIMITED"
    http_status = 429
    retryable = True


# ---------------------------------------------------------------------------
# Rules Engine
# ---------------------------------------------------------------------------
class RuleBlockedError(PlatformError):
    """Operation blocked by rules engine evaluation."""

    error_code = "RULE_BLOCKED"
    http_status = 403
    retryable = False

    def __init__(self, rule_id: str, message: str, **kwargs: Any) -> None:
        super().__init__(message, details={"blocking_rule": rule_id}, **kwargs)


# ---------------------------------------------------------------------------
# Kill Switch
# ---------------------------------------------------------------------------
class KillSwitchActiveError(PlatformError):
    """Operation blocked by active kill switch."""

    error_code = "KILL_SWITCH_ACTIVE"
    http_status = 503
    retryable = True  # Kill switch may be deactivated

    def __init__(self, switch_key: str, reason: str, **kwargs: Any) -> None:
        super().__init__(
            f"Kill switch active: {switch_key} — {reason}",
            details={"switch_key": switch_key, "reason": reason},
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------
class BulkheadExhaustedError(PlatformError):
    """Bulkhead semaphore pool exhausted. Prevent cascading failure."""

    error_code = "BULKHEAD_EXHAUSTED"
    http_status = 503
    retryable = True


# ---------------------------------------------------------------------------
# Non-retryable error type names for Temporal
# ---------------------------------------------------------------------------
NON_RETRYABLE_ERROR_TYPES: list[str] = [
    "ValidationError",
    "SchemaValidationError",
    "AuthorizationError",
    "TenantSuspendedError",
    "DuplicateOperationError",
    "OutputSchemaError",
    "LowConfidenceError",
    "PromptValidationError",
    "RuleBlockedError",
    "ApprovalRejectedError",
    "WorkflowBlockedError",
]
