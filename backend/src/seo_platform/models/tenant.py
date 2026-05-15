"""
SEO Platform — Domain Models: Tenant, User, Client
====================================================
Core entity models for multi-tenant platform identity.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TenantPlan(str, enum.Enum):
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    MANAGER = "manager"
    SEO_ANALYST = "seo_analyst"
    OUTREACH_SPECIALIST = "outreach_specialist"
    REPORT_ANALYST = "report_analyst"
    CLIENT = "client"


class OnboardingStatus(str, enum.Enum):
    PENDING = "pending"
    COLLECTING = "collecting"
    VALIDATING = "validating"
    AI_ENRICHMENT = "ai_enrichment"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETE = "complete"
    FAILED_VALIDATION = "failed_validation"
    AI_FAILED = "ai_failed"
    REJECTED = "rejected"


class BusinessType(str, enum.Enum):
    LOCAL = "local"
    NATIONAL = "national"
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    PUBLISHER = "publisher"


# ---------------------------------------------------------------------------
# Tenant Model
# ---------------------------------------------------------------------------
class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Top-level organizational entity.

    All data in the platform is owned by a Tenant. Row-Level Security
    policies enforce isolation at the database layer.
    """

    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[TenantPlan] = mapped_column(
        Enum(TenantPlan, name="tenant_plan", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TenantPlan.STARTER,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    users: Mapped[list[User]] = relationship("User", back_populates="tenant", lazy="selectin")
    clients: Mapped[list[Client]] = relationship("Client", back_populates="tenant", lazy="selectin")

    @property
    def is_suspended(self) -> bool:
        return self.suspended_at is not None

    @property
    def is_enterprise(self) -> bool:
        return self.plan == TenantPlan.ENTERPRISE


# ---------------------------------------------------------------------------
# User Model
# ---------------------------------------------------------------------------
class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Platform user belonging to a Tenant.

    Users authenticate via external provider (Clerk/Auth0).
    The external_id maps to the provider's user ID.
    """

    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.SEO_ANALYST,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="users")

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        # Role-based defaults + explicit overrides
        return permission in self.permissions or self._role_has_permission(permission)

    def _role_has_permission(self, permission: str) -> bool:
        """Check role-based default permissions (RBAC hierarchy)."""
        role_permissions = ROLE_PERMISSIONS.get(self.role, set())
        return permission in role_permissions


# ---------------------------------------------------------------------------
# Client Model
# ---------------------------------------------------------------------------
class Client(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """
    SEO client managed by a Tenant (agency's client).

    Each client has a domain, niche, geo-focus, and onboarding status.
    All downstream data (keywords, campaigns, reports) belongs to a Client.
    """

    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "domain", name="uq_client_tenant_domain"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    niche: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geo_focus: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    business_type: Mapped[BusinessType | None] = mapped_column(
        Enum(BusinessType, name="business_type", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    onboarding_status: Mapped[OnboardingStatus] = mapped_column(
        Enum(OnboardingStatus, name="onboarding_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OnboardingStatus.PENDING,
    )
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    competitors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="clients")


# ---------------------------------------------------------------------------
# Audit Log Model (Append-Only)
# ---------------------------------------------------------------------------
class AuditLog(Base, TimestampMixin):
    """
    Immutable audit trail for all system operations.

    This table is APPEND-ONLY. UPDATE and DELETE operations are
    prevented by a PostgreSQL trigger. Partitioned by month for
    performance at scale.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user | system | agent
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))


# ---------------------------------------------------------------------------
# Workflow Events (Event Sourcing)
# ---------------------------------------------------------------------------
class WorkflowEvent(Base, TimestampMixin):
    """
    Event sourcing table — system of record for all workflow state transitions.

    Current state of any entity is computed by replaying events from this table.
    Snapshots are maintained in workflow_snapshots (every 50 events).
    """

    __tablename__ = "workflow_events"
    __table_args__ = (
        UniqueConstraint("stream_id", "sequence_number", name="uq_workflow_event_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    stream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))


# ---------------------------------------------------------------------------
# RBAC Permission Matrix
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SUPER_ADMIN: {
        "launch_campaign", "approve_outreach", "view_all_clients",
        "create_keyword_cluster", "view_own_reports", "export_data",
        "manage_billing", "manage_users", "manage_rules", "manage_kill_switches",
        "view_audit_log", "manage_tenants",
    },
    UserRole.TENANT_ADMIN: {
        "launch_campaign", "approve_outreach", "view_all_clients",
        "create_keyword_cluster", "view_own_reports", "export_data",
        "manage_billing", "manage_users",
    },
    UserRole.MANAGER: {
        "approve_outreach", "view_all_clients", "create_keyword_cluster",
        "view_own_reports", "export_data",
    },
    UserRole.SEO_ANALYST: {
        "create_keyword_cluster", "view_own_reports",
    },
    UserRole.OUTREACH_SPECIALIST: {
        "create_keyword_cluster", "view_own_reports", "manage_outreach_threads",
    },
    UserRole.REPORT_ANALYST: {
        "view_own_reports", "generate_reports",
    },
    UserRole.CLIENT: {
        "view_own_reports",
    },
}
