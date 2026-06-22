"""
SEO Platform — Legacy Citation Models
======================================
Backwards-compatible re-exports. BusinessProfile moved to business_profile.py.
"""

from __future__ import annotations

import enum

# Re-export from new location (backwards compatibility)
from seo_platform.models.business_profile import BusinessProfile  # noqa: F401


class VerificationState(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    LIVE = "live"
    REMOVED = "removed"
    DUPLICATE = "duplicate"
    INCONSISTENT = "inconsistent"
