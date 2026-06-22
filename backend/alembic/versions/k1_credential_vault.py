"""k1_credential_vault

Revision ID: k1
Revises: j1
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "k1"
down_revision = "j1_add_citation_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create credential_status enum
    credential_status = postgresql.ENUM(
        "active", "suspended", "banned", "locked", "expired",
        name="credential_status",
        create_type=False,
    )
    credential_status.create(op.get_bind(), checkfirst=True)

    # Create credential_audit_action enum
    credential_audit_action = postgresql.ENUM(
        "created", "used", "success", "failure", "locked",
        "unlocked", "rotated", "deleted",
        name="credential_audit_action",
        create_type=False,
    )
    credential_audit_action.create(op.get_bind(), checkfirst=True)

    # directory_credentials table
    op.create_table(
        "directory_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("site_slug", sa.String(100), nullable=False, index=True),
        sa.Column("site_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_encrypted", sa.Text, nullable=False),
        sa.Column("recovery_email", sa.String(255)),
        sa.Column("recovery_phone", sa.String(50)),
        sa.Column("status", postgresql.ENUM("active", "suspended", "banned", "locked", "expired", name="credential_status", create_type=False), nullable=False, server_default="active"),
        sa.Column("health_score", sa.Integer, nullable=False, server_default="100"),
        sa.Column("use_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_reason", sa.Text),
        sa.Column("rotation_scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("rotation_completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_directory_credentials_tenant", "directory_credentials", ["tenant_id"])
    op.create_index("ix_directory_credentials_site_slug", "directory_credentials", ["site_slug"])
    op.create_index("ix_directory_credentials_status", "directory_credentials", ["status"])

    # credential_audit_log table
    op.create_table(
        "credential_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("directory_credentials.id", ondelete="SET NULL"), index=True),
        sa.Column("action", postgresql.ENUM("created", "used", "success", "failure", "locked", "unlocked", "rotated", "deleted", name="credential_audit_action", create_type=False), nullable=False),
        sa.Column("site_slug", sa.String(100)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text),
        sa.Column("failure_reason", sa.Text),
        sa.Column("metadata_json", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_credential_audit_log_tenant", "credential_audit_log", ["tenant_id"])
    op.create_index("ix_credential_audit_log_credential", "credential_audit_log", ["credential_id"])
    op.create_index("ix_credential_audit_log_action", "credential_audit_log", ["action"])


def downgrade() -> None:
    op.drop_table("credential_audit_log")
    op.drop_table("directory_credentials")
    postgresql.ENUM(name="credential_audit_action").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="credential_status").drop(op.get_bind(), checkfirst=True)
