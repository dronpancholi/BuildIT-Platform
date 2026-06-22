"""add_updated_at_to_model_backed_tables

Phase 1.3.1 — Database Integrity Recovery (continuation, round 4).

Several tables that the ORM expects to have updated_at (via TimestampMixin
or explicit declaration) are missing that column in the live database.
This migration adds it to the model-backed tables that need it for ORM
queries to succeed.

Affected tables (model-backed, TimestampMixin or explicit updated_at):
- action_definitions   (TimestampMixin)
- agent_tasks          (TimestampMixin)
- reports              (TimestampMixin)
- graph_entities       (explicit updated_at declaration)

Tables intentionally skipped:
- _test_xyz            (test artifact, no model)
- operational_events   (runtime-created, no model, no updated_at needed)
- graph_edges          (model explicitly has no updated_at)
- email_templates, outreach_emails (models exist but no TimestampMixin)
- automation_*, executive_metrics_snapshots, node_dependencies,
  plan_forecasts, plan_nodes, processed_webhook_events (pure DB tables,
  no ORM model, so no SELECT to updated_at occurs)
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "i16_add_updated_at_columns"
down_revision: Union[str, None] = "i15_add_action_def_max_retries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for tbl in ["action_definitions", "agent_tasks", "reports", "graph_entities"]:
        op.execute(
            f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;"
        )


def downgrade() -> None:
    for tbl in ["action_definitions", "agent_tasks", "reports", "graph_entities"]:
        op.execute(f"ALTER TABLE {tbl} DROP COLUMN IF EXISTS updated_at;")
