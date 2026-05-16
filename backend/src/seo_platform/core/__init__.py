"""
SEO Platform — Core Package

Centralized foundational infrastructure for the entire platform.
All modules use absolute imports from `seo_platform.core.*`.
"""

from seo_platform.core.errors import (
    NON_RETRYABLE_ERROR_TYPES,
    ConfigurationError,
    PlatformError,
    SemanticGroundingError,
)
from seo_platform.core.logging import (
    WorkflowSafeLogger,
    get_logger,
    get_workflow_logger,
    setup_logging,
)

__all__ = [
    "NON_RETRYABLE_ERROR_TYPES",
    "ConfigurationError",
    "PlatformError",
    "SemanticGroundingError",
    "WorkflowSafeLogger",
    "get_logger",
    "get_workflow_logger",
    "setup_logging",
]
