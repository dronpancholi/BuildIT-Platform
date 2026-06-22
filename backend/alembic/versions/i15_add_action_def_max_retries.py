"""add_action_definitions_max_retries

Phase 1.3.1 — Database Integrity Recovery (continuation, round 3).

The earlier i14 migration missed the `max_retries` column on
action_definitions. This adds it with the default value the model expects.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "i15_add_action_def_max_retries"
down_revision: Union[str, None] = "i14_align_action_definitions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE action_definitions ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3;")


def downgrade() -> None:
    op.execute("ALTER TABLE action_definitions DROP COLUMN IF EXISTS max_retries;")
