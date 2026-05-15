"""
SEO Platform — Models Package
================================
All SQLAlchemy ORM models are registered here for Alembic discovery.
"""

from seo_platform.models.approval import (
    ApprovalRequestModel,
)
from seo_platform.models.backlink import (
    AcquiredLink,
    BacklinkCampaign,
    BacklinkProspect,
    OutreachThread,
)
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin
from seo_platform.models.business_memory import (
    BusinessIntelligenceEvent,
    CampaignHealthSnapshot,
    KeywordMetricSnapshot,
    ProspectScoreHistory,
    RecommendationModel,
    SerpVolatilitySnapshot,
)
from seo_platform.models.citation import (
    BusinessProfile,
    CitationSubmission,
)
from seo_platform.models.communication import (
    EmailTemplate,
    OutreachEmail,
)
from seo_platform.models.keywords import KeywordResearch
from seo_platform.models.seo import (
    Keyword,
    KeywordCluster,
)
from seo_platform.models.tenant import (
    AuditLog,
    Client,
    Tenant,
    User,
    WorkflowEvent,
)

__all__ = [
    "Base",
    "TenantMixin",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    # Core
    "AuditLog",
    "Client",
    "Tenant",
    "User",
    "WorkflowEvent",
    # SEO Intelligence
    "Keyword",
    "KeywordCluster",
    "KeywordResearch",
    # Backlink Engine
    "AcquiredLink",
    "BacklinkCampaign",
    "BacklinkProspect",
    "BusinessIntelligenceEvent",
    "BusinessProfile",
    "CampaignHealthSnapshot",
    "CitationSubmission",
    "Client",
    "EmailTemplate",
    "Keyword",
    "KeywordCluster",
    "KeywordMetricSnapshot",
    "KeywordResearch",
    "OutreachEmail",
    "OutreachThread",
    "ProspectScoreHistory",
    "RecommendationModel",
    "SerpVolatilitySnapshot",
    "Tenant",
    "User",
    "WorkflowEvent",
]
