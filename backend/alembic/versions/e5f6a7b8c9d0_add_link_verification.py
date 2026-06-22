"""add_link_verification

Revision ID: e5f6a7b8c9d0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-01 09:00:00.000000

Adds link verification history and last-known HTTP telemetry to
``acquired_links`` so the link verification engine can persist full
per-check snapshots and the link monitoring engine can compare deltas
across scheduled runs.

Also adds the standard RLS tenant-isolation policies for any tables
created or mutated by this revision (PostgreSQL RLS is enforced on
every tenant-scoped table in the platform).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
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
    # acquired_links: append verification telemetry columns
    op.add_column(
        "acquired_links",
        sa.Column(
            "verification_history",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "acquired_links",
        sa.Column("last_http_status", sa.Integer(), nullable=True),
    )
    op.add_column(
        "acquired_links",
        sa.Column("last_response_time_ms", sa.Float(), nullable=True),
    )
    op.add_column(
        "acquired_links",
        sa.Column("last_checked_redirect_chain", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "acquired_links",
        sa.Column("last_match_anchor", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "acquired_links",
        sa.Column("last_match_rel", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "acquired_links",
        sa.Column("last_match_position", sa.Integer(), nullable=True),
    )
    op.add_column(
        "acquired_links",
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_acquired_links_status"),
        "acquired_links",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_acquired_links_last_checked_at"),
        "acquired_links",
        ["last_checked_at"],
        unique=False,
    )

    # RLS policies for acquired_links (idempotent — uses IF NOT EXISTS-like guards)
    _ensure_rls("acquired_links", "tenant_id")


def downgrade() -> None:
    op.drop_index(op.f("ix_acquired_links_last_checked_at"), table_name="acquired_links")
    op.drop_index(op.f("ix_acquired_links_status"), table_name="acquired_links")
    op.drop_column("acquired_links", "last_error")
    op.drop_column("acquired_links", "last_match_position")
    op.drop_column("acquired_links", "last_match_rel")
    op.drop_column("acquired_links", "last_match_anchor")
    op.drop_column("acquired_links", "last_checked_redirect_chain")
    op.drop_column("acquired_links", "last_response_time_ms")
    op.drop_column("acquired_links", "last_http_status")
    op.drop_column("acquired_links", "verification_history")
