"""add_outreach_communication_tables

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-02 11:15:00.000000

Brings ``email_drafts``, ``communication_templates``, and
``scheduled_emails`` under alembic control so a fresh ``alembic upgrade
head`` on an empty database produces the full schema the engine needs.
Previously these tables were created by app startup (or were missing
entirely on a fresh DB), which caused a 500 on the first request that
needed them.

Each table is tenant-scoped, so RLS isolation policies are added in
the same step.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str, None], None] = None
depends_on: Union[str, Sequence[str, None], None] = None


_RLS_SELECT = "CREATE POLICY {name}_sel ON {table} FOR SELECT USING ({col} = current_setting('app.current_tenant')::uuid)"
_RLS_INSERT = "CREATE POLICY {name}_ins ON {table} FOR INSERT WITH CHECK ({col} = current_setting('app.current_tenant')::uuid)"
_RLS_UPDATE = "CREATE POLICY {name}_upd ON {table} FOR UPDATE USING ({col} = current_setting('app.current_tenant')::uuid) WITH CHECK ({col} = current_setting('app.current_tenant')::uuid)"
_RLS_DELETE = "CREATE POLICY {name}_del ON {table} FOR DELETE USING ({col} = current_setting('app.current_tenant')::uuid)"


def _ensure_rls(table: str, tenant_col: str) -> None:
    """Enable RLS and create per-statement policies if not already present."""
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    policy_name = f"{table}_tenant_isolation"
    op.execute(_RLS_SELECT.format(name=policy_name, table=table, col=tenant_col))
    op.execute(_RLS_INSERT.format(name=policy_name, table=table, col=tenant_col))
    op.execute(_RLS_UPDATE.format(name=policy_name, table=table, col=tenant_col))
    op.execute(_RLS_DELETE.format(name=policy_name, table=table, col=tenant_col))


def upgrade() -> None:
    # ------------------------------------------------------------------
    # email_drafts — pre-render of an outreach email before send
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS email_drafts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            template_id VARCHAR(255),
            subject VARCHAR(500) NOT NULL,
            body_html TEXT NOT NULL,
            to_email VARCHAR(255),
            variables JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_drafts_tenant_id ON email_drafts(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_drafts_status ON email_drafts(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_drafts_tenant ON email_drafts(tenant_id)")
    _ensure_rls("email_drafts", "tenant_id")

    # ------------------------------------------------------------------
    # communication_templates — reusable email/pitch templates
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            category VARCHAR(50) NOT NULL,
            subject VARCHAR(500) NOT NULL,
            body TEXT NOT NULL,
            variables JSONB NOT NULL DEFAULT '[]'::jsonb,
            is_archived BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_communication_templates_category ON communication_templates(category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_communication_templates_tenant ON communication_templates(tenant_id)")
    _ensure_rls("communication_templates", "tenant_id")

    # ------------------------------------------------------------------
    # scheduled_emails — outbound queue with scheduled send windows
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_emails (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            thread_id VARCHAR(255) NOT NULL,
            subject VARCHAR(500) NOT NULL,
            to_email VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            scheduled_at TIMESTAMPTZ NOT NULL,
            timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ,
            sent_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_emails_tenant_id ON scheduled_emails(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scheduled_emails_status ON scheduled_emails(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scheduled_emails_tenant ON scheduled_emails(tenant_id)")
    _ensure_rls("scheduled_emails", "tenant_id")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scheduled_emails_tenant")
    op.execute("DROP INDEX IF EXISTS ix_scheduled_emails_status")
    op.execute("DROP INDEX IF EXISTS idx_scheduled_emails_tenant_id")
    op.execute("DROP TABLE IF EXISTS scheduled_emails")

    op.execute("DROP INDEX IF EXISTS ix_communication_templates_tenant")
    op.execute("DROP INDEX IF EXISTS ix_communication_templates_category")
    op.execute("DROP TABLE IF EXISTS communication_templates")

    op.execute("DROP INDEX IF EXISTS ix_email_drafts_tenant")
    op.execute("DROP INDEX IF EXISTS ix_email_drafts_status")
    op.execute("DROP INDEX IF EXISTS idx_email_drafts_tenant_id")
    op.execute("DROP TABLE IF EXISTS email_drafts")
