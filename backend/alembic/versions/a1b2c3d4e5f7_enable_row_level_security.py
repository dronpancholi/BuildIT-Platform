"""enable_row_level_security

Revision ID: a1b2c3d4e5f7
Revises: f1b2c3d4e5f6
Create Date: 2026-05-27 14:00:00.000000

Enables Row-Level Security (RLS) on all tenant‑scoped tables and creates
policies that enforce tenant isolation via the `app.current_tenant` session
variable (set by ``get_tenant_session()``).

Reversible — the downgrade drops all policies and disables RLS.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that carry a tenant_id and require RLS policies.
# Each tuple is (tablename, tenant_id_column_name).
TENANT_TABLES: list[tuple[str, str]] = [
    # Planning
    ("execution_plans", "tenant_id"),
    ("plan_nodes", "tenant_id"),
    ("node_dependencies", "tenant_id"),
    ("plan_forecasts", "tenant_id"),
    # Agents
    ("agent_definitions", "tenant_id"),
    ("agent_instances", "tenant_id"),
    ("agent_tasks", "tenant_id"),
    ("agent_conflicts", "tenant_id"),
    # Goals
    ("goal_definitions", "tenant_id"),
    ("goal_executions", "tenant_id"),
    # Approvals
    ("approval_requests", "tenant_id"),
    ("approval_requests_v2", "tenant_id"),
    ("approval_policies", "tenant_id"),
    # Actions
    ("action_definitions", "tenant_id"),
    ("action_executions", "tenant_id"),
    # Audit
    ("audit_ledger", "tenant_id"),
    # Memory
    ("operational_memory", "tenant_id"),
    # Knowledge graph
    ("graph_entities", "tenant_id"),
    ("graph_edges", "tenant_id"),
    # Operational telemetry / business memory
    ("clients", "tenant_id"),
    ("contacts", "tenant_id"),
    ("backlink_campaigns", "tenant_id"),
    ("backlink_prospects", "tenant_id"),
    ("outreach_threads", "tenant_id"),
    ("acquired_links", "tenant_id"),
    ("keywords", "tenant_id"),
    ("keyword_clusters", "tenant_id"),
    ("keyword_research", "tenant_id"),
    ("reports", "tenant_id"),
    ("outreach_emails", "tenant_id"),
    ("email_templates", "tenant_id"),
    ("campaign_timeline_events", "tenant_id"),
    ("compliance_results", "tenant_id"),
    ("business_profiles", "tenant_id"),
    ("citation_submissions", "tenant_id"),
    ("campaign_health_snapshots", "tenant_id"),
    ("keyword_metric_snapshots", "tenant_id"),
    ("serp_volatility_snapshots", "tenant_id"),
    ("business_intelligence_events", "tenant_id"),
    ("recommendations", "tenant_id"),
    ("prospect_score_history", "tenant_id"),
]

# Policy templates
_POLICY_NAME = "{table}_tenant_isolation"
_SELECT_POLICY = "CREATE POLICY {name} ON {table} FOR SELECT USING ({col} = current_setting('app.current_tenant')::uuid)"
_INSERT_POLICY = "CREATE POLICY {name} ON {table} FOR INSERT WITH CHECK ({col} = current_setting('app.current_tenant')::uuid)"
_UPDATE_POLICY = "CREATE POLICY {name} ON {table} FOR UPDATE USING ({col} = current_setting('app.current_tenant')::uuid) WITH CHECK ({col} = current_setting('app.current_tenant')::uuid)"
_DELETE_POLICY = "CREATE POLICY {name} ON {table} FOR DELETE USING ({col} = current_setting('app.current_tenant')::uuid)"


def _enable_rls(table: str, col: str) -> None:
    """Enable RLS and create per‑statement policies for a table."""
    name = _POLICY_NAME.format(table=table)
    # Enable RLS
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    # Force RLS for table owners too (superusers still bypass)
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    # Create policies
    op.execute(_SELECT_POLICY.format(name=name, table=table, col=col))
    op.execute(_INSERT_POLICY.format(name=name, table=table, col=col))
    op.execute(_UPDATE_POLICY.format(name=name, table=table, col=col))
    op.execute(_DELETE_POLICY.format(name=name, table=table, col=col))


def _disable_rls(table: str, col: str) -> None:  # noqa: ARG001
    """Drop all policies and disable RLS for a table."""
    name = _POLICY_NAME.format(table=table)
    op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    for table, col in TENANT_TABLES:
        _enable_rls(table, col)


def downgrade() -> None:
    for table, col in reversed(TENANT_TABLES):
        _disable_rls(table, col)
