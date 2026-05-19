"""
SEO Platform — SEO Provider Abstraction
========================================
DEPRECATED — Use seo_platform.providers.seo instead.

This module is kept for backward compatibility and redirects to the unified
provider registry in seo_platform.providers.seo.
"""

from __future__ import annotations

import warnings

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

warnings.warn(
    "seo_platform.services.seo_provider is deprecated. "
    "Use seo_platform.providers.seo.get_seo_provider() instead.",
    DeprecationWarning,
    stacklevel=2,
)
logger.warning("deprecated_module_accessed", module="seo_platform.services.seo_provider")

from seo_platform.providers.seo import get_seo_provider  # noqa: E402, F401
