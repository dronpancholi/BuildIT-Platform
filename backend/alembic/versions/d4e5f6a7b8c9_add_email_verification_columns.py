"""add_email_verification_columns

Revision ID: d4e5f6a7b8c9
Revises: c4d5e6f7a8b9
Create Date: 2026-06-01 12:00:00.000000

Phase 1.2 — Workstream C
Adds email verification columns to backlink_prospects and ensures RLS
policies exist (idempotent — the table was already RLS-enabled in
``a1b2c3d4e5f7_enable_row_level_security``, but we re-assert the four
per-statement policies in case a fresh database missed them).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE = "backlink_prospects"
_TENANT_COL = "tenant_id"
_POLICY_NAME = "backlink_prospects_tenant_isolation"

_SELECT_POLICY = (
    "CREATE POLICY {name} ON {table} FOR SELECT "
    "USING ({col} = current_setting('app.current_tenant')::uuid)"
)
_INSERT_POLICY = (
    "CREATE POLICY {name} ON {table} FOR INSERT "
    "WITH CHECK ({col} = current_setting('app.current_tenant')::uuid)"
)
_UPDATE_POLICY = (
    "CREATE POLICY {name} ON {table} FOR UPDATE "
    "USING ({col} = current_setting('app.current_tenant')::uuid) "
    "WITH CHECK ({col} = current_setting('app.current_tenant')::uuid)"
)
_DELETE_POLICY = (
    "CREATE POLICY {name} ON {table} FOR DELETE "
    "USING ({col} = current_setting('app.current_tenant')::uuid)"
)


def upgrade() -> None:
    # 1. Add the two new columns
    op.add_column(
        _TABLE,
        sa.Column(
            "email_verification_status",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'unverified'"),
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "email_verification_result",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # 2. Idempotent RLS policy creation
    # The table was already RLS-enabled in a1b2c3d4e5f7, but on freshly
    # provisioned databases that migration may not have run for this table.
    # Use DO blocks so re-running this migration is safe.
    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY")

    # Use dollar-quoted strings to avoid the inner single-quote escaping nightmare.
    op.execute(
        f"""
        DO $do$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = current_schema()
                  AND tablename = '{_TABLE}'
                  AND policyname = '{_POLICY_NAME}'
            ) THEN
                EXECUTE $pol$CREATE POLICY {_POLICY_NAME} ON {_TABLE} FOR SELECT
                    USING ({_TENANT_COL} = current_setting($q$app.current_tenant$q$)::uuid)$pol$;
                EXECUTE $pol$CREATE POLICY {_POLICY_NAME} ON {_TABLE} FOR INSERT
                    WITH CHECK ({_TENANT_COL} = current_setting($q$app.current_tenant$q$)::uuid)$pol$;
                EXECUTE $pol$CREATE POLICY {_POLICY_NAME} ON {_TABLE} FOR UPDATE
                    USING ({_TENANT_COL} = current_setting($q$app.current_tenant$q$)::uuid)
                    WITH CHECK ({_TENANT_COL} = current_setting($q$app.current_tenant$q$)::uuid)$pol$;
                EXECUTE $pol$CREATE POLICY {_POLICY_NAME} ON {_TABLE} FOR DELETE
                    USING ({_TENANT_COL} = current_setting($q$app.current_tenant$q$)::uuid)$pol$;
            END IF;
        END$do$;
        """
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "email_verification_result")
    op.drop_column(_TABLE, "email_verification_status")
    # We do not drop the RLS policy on downgrade because other
    # migrations / production environments still need it.
