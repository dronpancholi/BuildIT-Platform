"""
SEO Platform — Models Package
================================
All SQLAlchemy ORM models are registered here for Alembic discovery.
"""

from seo_platform.core.database import Base
from seo_platform.models.approval import (
    ApprovalRequestModel,
)
from seo_platform.models.approval_policy import (
    ApprovalPolicy,
    ApprovalRequest,
)
from seo_platform.models.action import (
    ActionDefinition,
    ActionExecution,
)
from seo_platform.models.audit_ledger import (
    AuditLedgerEntry,
)
from seo_platform.models.provider_key import (
    ProviderKey,
)
from seo_platform.models.operational_memory import (
    MemoryEntry,
)
# Agent orchestration models
from seo_platform.models.agent import (
    AgentDefinition,
    AgentInstance,
    AgentTask,
    AgentConflict,
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
from seo_platform.models.business_profile import (
    BusinessProfile,
)
from seo_platform.models.citation_v2 import (
    CitationSite,
    CitationProject,
    CitationSubmissionV2,
)
from seo_platform.models.credential_vault import (
    DirectoryCredential,
    CredentialAuditLog,
)
from seo_platform.models.rate_limiting import (
    ProxyPool,
    RateLimitConfig,
)
from seo_platform.models.recommendations import (
    CitationRecommendation,
    CompetitorCitation,
)
from seo_platform.models.communication import (
    EmailTemplate,
    OutreachEmail,
)
from seo_platform.models.keywords import KeywordResearch
from seo_platform.models.observability import (
    AuditTrailLog,
    CampaignTimelineEvent,
    ComplianceResult,
    ProviderHealthMetric,
)
from seo_platform.models.seo import (
    Keyword,
    KeywordCluster,
)
from seo_platform.models.knowledge_graph import (
    GraphEntity,
    GraphEdge,
)
from seo_platform.models.tenant import (
    AuditLog,
    Client,
    Tenant,
    User,
    WorkflowEvent,
)
from seo_platform.models.contact import Contact
# Goal orchestration models
from seo_platform.models.goal import GoalDefinition, GoalExecution
from seo_platform.models.planning import ExecutionPlan, PlanNode, NodeDependency, PlanForecast
from seo_platform.models.seo_task import SEOTask, TaskStatus, TaskPriority, TaskSource

__all__ = [
    "Base",
    "TenantMixin",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    # Core
    "AuditLog",
    # Observability
    "AuditTrailLog",
    "CampaignTimelineEvent",
    "ComplianceResult",
    "ProviderHealthMetric",
    "GraphEntity",
    "GraphEdge",
    "Client",
    "Tenant",
    "User",
    "WorkflowEvent",
    # SEO Intelligence
    "Keyword",
    "KeywordCluster",
    "KeywordResearch",
    "ProviderKey",
    # Backlink Engine
    "AcquiredLink",
    "BacklinkCampaign",
    "BacklinkProspect",
    "BusinessIntelligenceEvent",
    "BusinessProfile",
    "CampaignHealthSnapshot",
    "CitationSite",
    "CitationProject",
    "CitationSubmissionV2",
    "DirectoryCredential",
    "CredentialAuditLog",
    "ProxyPool",
    "RateLimitConfig",
    "EmailTemplate",
    "KeywordMetricSnapshot",
    "OutreachEmail",
    "OutreachThread",
    "ProspectScoreHistory",
    "RecommendationModel",
    "SerpVolatilitySnapshot",
    "Contact",
    "GoalDefinition",
    "GoalExecution", "ExecutionPlan", "PlanNode", "NodeDependency", "PlanForecast",
    "SEOTask", "TaskStatus", "TaskPriority", "TaskSource",
]
