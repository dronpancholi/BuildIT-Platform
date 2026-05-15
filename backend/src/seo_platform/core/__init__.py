"""
SEO Platform — Core Package
"""

from seo_platform.core.errors import PlatformError
from seo_platform.core.logging import get_logger, setup_logging

__all__ = ["PlatformError", "get_logger", "setup_logging"]
