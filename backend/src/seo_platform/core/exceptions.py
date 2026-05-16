"""
SEO Platform — Exception Hierarchy Re-Export
==============================================
Convenience alias module. All exception classes are defined in `errors.py`.
This module re-exports them for import ergonomics.

Usage:
    from seo_platform.core.exceptions import (
        PlatformError, SemanticGroundingError, ConfigurationError,
    )
"""

from seo_platform.core.errors import (
    ApprovalRejectedError,
    ApprovalRequiredError,
    AuthenticationError,
    AuthorizationError,
    BulkheadExhaustedError,
    CircuitOpenError,
    ConfigurationError,
    DuplicateEntityError,
    DuplicateOperationError,
    EntityNotFoundError,
    ExternalServiceError,
    KillSwitchActiveError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LowConfidenceError,
    OutputSchemaError,
    PlatformError,
    PromptValidationError,
    RateLimitedError,
    RuleBlockedError,
    SchemaValidationError,
    SemanticGroundingError,
    TenantError,
    TenantNotFoundError,
    TenantQuotaExceededError,
    TenantSuspendedError,
    TokenExpiredError,
    ValidationError,
    WorkflowBlockedError,
    WorkflowError,
)

__all__ = [
    "ApprovalRejectedError",
    "ApprovalRequiredError",
    "AuthenticationError",
    "AuthorizationError",
    "BulkheadExhaustedError",
    "CircuitOpenError",
    "ConfigurationError",
    "DuplicateEntityError",
    "DuplicateOperationError",
    "EntityNotFoundError",
    "ExternalServiceError",
    "KillSwitchActiveError",
    "LLMError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LowConfidenceError",
    "OutputSchemaError",
    "PlatformError",
    "PromptValidationError",
    "RateLimitedError",
    "RuleBlockedError",
    "SchemaValidationError",
    "SemanticGroundingError",
    "TenantError",
    "TenantNotFoundError",
    "TenantQuotaExceededError",
    "TenantSuspendedError",
    "TokenExpiredError",
    "ValidationError",
    "WorkflowBlockedError",
    "WorkflowError",
]
