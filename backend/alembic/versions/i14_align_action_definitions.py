"""align_action_definitions_with_phase14_model

Phase 1.3.1 — Database Integrity Recovery (continuation).

The action_definitions table was created as a stub in
f2c3d4e5f6g7_add_planning_engine_tables.py with only the columns needed
for FK references. The Phase 14 model (src/seo_platform/models/action.py)
expects a richer schema with classification, governance, and execution
fields. This migration adds those columns and the two enum types they
depend on.

Revision ID: i14_align_action_definitions
Revises: i13_recover_missing_tables
Create Date: 2026-06-05
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "i14_align_action_definitions"
down_revision: Union[str, None] = "i13_recover_missing_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing enum types and columns to action_definitions."""

    # ------------------------------------------------------------------
    # 1. Enum types
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE action_category AS ENUM (
                'crm','campaign','communication','analytics','workflow','integration'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE action_risk_level AS ENUM ('low','medium','high','critical');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ------------------------------------------------------------------
    # 2. Add missing columns to action_definitions
    #    The table is empty (verified before this migration), so NOT NULL
    #    columns can be added with sensible defaults.
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS display_name VARCHAR(255);")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS category action_category;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS risk_level action_risk_level;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS input_schema JSONB NOT NULL DEFAULT '{}'::jsonb;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS output_schema JSONB;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS permission_required VARCHAR(100);")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN NOT NULL DEFAULT TRUE;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS approval_policy JSONB;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS rollback_handler VARCHAR(255);")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS execution_timeout_seconds INTEGER NOT NULL DEFAULT 300;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS idempotent BOOLEAN NOT NULL DEFAULT FALSE;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;")
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS custom_metadata JSONB;")

    # Backfill NOT NULL text/enum columns with safe defaults so the existing
    # zero-row baseline is valid. Production inserts must supply real values.
    op.execute("UPDATE action_definitions SET display_name = name WHERE display_name IS NULL;")
    op.execute("UPDATE action_definitions SET permission_required = 'system' WHERE permission_required IS NULL;")
    op.execute("UPDATE action_definitions SET category = 'workflow'::action_category WHERE category IS NULL;")
    op.execute("UPDATE action_definitions SET risk_level = 'low'::action_risk_level WHERE risk_level IS NULL;")

    op.execute("ALTER TABLE action_definitions ALTER COLUMN display_name SET NOT NULL;")
    op.execute("ALTER TABLE action_definitions ALTER COLUMN permission_required SET NOT NULL;")
    op.execute("ALTER TABLE action_definitions ALTER COLUMN category SET NOT NULL;")
    op.execute("ALTER TABLE action_definitions ALTER COLUMN risk_level SET NOT NULL;")

    # ------------------------------------------------------------------
    # 3. Add the composite index the model declares
    # ------------------------------------------------------------------
    op.execute("CREATE INDEX IF NOT EXISTS ix_action_def_tenant_category ON action_definitions(tenant_id, category);")


def downgrade() -> None:
    """Remove added columns and enum types."""
    op.execute("DROP INDEX IF EXISTS ix_action_def_tenant_category;")

    for col in [
        "custom_metadata","version","is_enabled","idempotent",
        "max_retries","execution_timeout_seconds","rollback_handler",
        "approval_policy","requires_approval","permission_required",
        "output_schema","input_schema","risk_level","category","display_name",
    ]:
        op.execute(f"ALTER TABLE action_definitions DROP COLUMN IF EXISTS {col};")

    op.execute("DROP TYPE IF EXISTS action_risk_level;")
    op.execute("DROP TYPE IF EXISTS action_category;")
