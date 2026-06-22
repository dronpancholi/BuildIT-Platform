"""add_planning_engine_tables

Revision ID: a2b3c4d5e6f7
Revises: f1b2c3d4e5f6
Create Date: 2026-05-27 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create planning engine tables.

    Tables:
    - action_definitions (stub, for FK)
    - execution_plans
    - plan_nodes
    - node_dependencies
    - plan_forecasts
    """
    # Stub table for action_definitions FK (will be populated in a later phase)
    op.create_table(
        "action_definitions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_action_definitions_tenant_id"), "action_definitions", ["tenant_id"], unique=False)

    # execution_plans
    op.create_table(
        "execution_plans",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("goal_execution_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'generated'")),
        sa.Column("plan_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("generated_by", sa.String(length=50), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("plan_summary", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("plan_graph", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("simulation_result", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_execution_id"], ["goal_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_execution_plans_tenant_id"), "execution_plans", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_execution_plans_status"), "execution_plans", ["status"], unique=False)
    op.create_index(op.f("ix_execution_plans_goal_execution_id"), "execution_plans", ["goal_execution_id"], unique=False)

    # plan_nodes
    op.create_table(
        "plan_nodes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("node_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_agent", sa.UUID(), nullable=True),
        sa.Column("action_definition_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("dependency_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["execution_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["action_definition_id"], ["action_definitions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_nodes_tenant_id"), "plan_nodes", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_plan_nodes_plan_id"), "plan_nodes", ["plan_id"], unique=False)
    op.create_index(op.f("ix_plan_nodes_status"), "plan_nodes", ["status"], unique=False)

    # node_dependencies
    op.create_table(
        "node_dependencies",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("source_node_id", sa.UUID(), nullable=False),
        sa.Column("target_node_id", sa.UUID(), nullable=False),
        sa.Column("dependency_type", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["execution_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_node_id"], ["plan_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["plan_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_node_dependencies_tenant_id"), "node_dependencies", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_node_dependencies_plan_id"), "node_dependencies", ["plan_id"], unique=False)

    # plan_forecasts
    op.create_table(
        "plan_forecasts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("completion_probability", sa.Float(), nullable=True),
        sa.Column("risk_projection", sa.Float(), nullable=True),
        sa.Column("execution_projection", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("bottleneck_prediction", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["execution_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_forecasts_tenant_id"), "plan_forecasts", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_plan_forecasts_plan_id"), "plan_forecasts", ["plan_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_forecasts_plan_id"), table_name="plan_forecasts")
    op.drop_index(op.f("ix_plan_forecasts_tenant_id"), table_name="plan_forecasts")
    op.drop_table("plan_forecasts")

    op.drop_index(op.f("ix_node_dependencies_plan_id"), table_name="node_dependencies")
    op.drop_index(op.f("ix_node_dependencies_tenant_id"), table_name="node_dependencies")
    op.drop_table("node_dependencies")

    op.drop_index(op.f("ix_plan_nodes_status"), table_name="plan_nodes")
    op.drop_index(op.f("ix_plan_nodes_plan_id"), table_name="plan_nodes")
    op.drop_index(op.f("ix_plan_nodes_tenant_id"), table_name="plan_nodes")
    op.drop_table("plan_nodes")

    op.drop_index(op.f("ix_execution_plans_goal_execution_id"), table_name="execution_plans")
    op.drop_index(op.f("ix_execution_plans_status"), table_name="execution_plans")
    op.drop_index(op.f("ix_execution_plans_tenant_id"), table_name="execution_plans")
    op.drop_table("execution_plans")

    op.drop_index(op.f("ix_action_definitions_tenant_id"), table_name="action_definitions")
    op.drop_table("action_definitions")
