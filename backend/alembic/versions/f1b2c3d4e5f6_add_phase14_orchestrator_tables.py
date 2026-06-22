"""add_phase14_orchestrator_tables

Revision ID: f1b2c3d4e5f6
Revises: 2a3b4c5d6e7f
Create Date: 2026-05-27 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f1b2c3d4e5f6"
down_revision: Union[str, None] = "2a3b4c5d6e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables required for the Phase 14 orchestrator.

    The tables match the ORM definitions in ``seo_platform.models.agent`` and
    ``seo_platform.models.goal``.
    """
    # ---------------------------------------------------------------------
    # Agent definitions – static catalog of agent types
    # ---------------------------------------------------------------------
    op.create_table(
        "agent_definitions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("agent_type", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_agent_def_tenant_name"),
    )
    op.create_index(op.f("ix_agent_definitions_tenant_id"), "agent_definitions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_agent_definitions_enabled"), "agent_definitions", ["enabled"], unique=False)
    op.create_index(op.f("ix_agent_definitions_priority"), "agent_definitions", ["priority"], unique=False)

    # ---------------------------------------------------------------------
    # Agent instances – runtime incarnation of a definition
    # ---------------------------------------------------------------------
    op.create_table(
        "agent_instances",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("definition_id", sa.UUID(), nullable=False),
        sa.Column("running_state", sa.String(length=50), nullable=False),
        sa.Column("health_state", sa.String(length=50), nullable=False),
        sa.Column("execution_counters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["definition_id"], ["agent_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "definition_id", name="uq_agent_instance_tenant_def"),
    )
    op.create_index(op.f("ix_agent_instances_tenant_id"), "agent_instances", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_agent_instances_definition_id"), "agent_instances", ["definition_id"], unique=False)

    # ---------------------------------------------------------------------
    # Agent tasks – work items scheduled for a specific instance
    # ---------------------------------------------------------------------
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_instance_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("urgency", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("execution_reference", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_instance_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_agent_tasks_tenant_state", "tenant_id", "status"),
    )
    op.create_index(op.f("ix_agent_tasks_tenant_id"), "agent_tasks", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_agent_tasks_status"), "agent_tasks", ["status"], unique=False)

    # ---------------------------------------------------------------------
    # Agent conflicts – detection of overlapping work across agents
    # ---------------------------------------------------------------------
    op.create_table(
        "agent_conflicts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("conflict_type", sa.String(length=50), nullable=False),
        sa.Column("involved_agents", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("resolution_strategy", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'detected'")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_conflicts_tenant_id"), "agent_conflicts", ["tenant_id"], unique=False)

    # ---------------------------------------------------------------------
    # Goal definitions – static description of a business objective
    # ---------------------------------------------------------------------
    op.create_table(
        "goal_definitions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_goal_def_tenant_name"),
    )
    op.create_index(op.f("ix_goal_definitions_tenant_id"), "goal_definitions", ["tenant_id"], unique=False)

    # ---------------------------------------------------------------------
    # Goal executions – runtime instance of a goal
    # ---------------------------------------------------------------------
    op.create_table(
        "goal_executions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("definition_id", sa.UUID(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "new",
                "planning",
                "ready",
                "running",
                "waiting_approval",
                "failed",
                "completed",
                "cancelled",
                name="goal_state",
                create_constraint=True,
                values_callable=lambda x: [e.value for e in x],
            ),
            nullable=False,
            server_default=sa.text("'new'"),
        ),
        sa.Column("outcome_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["definition_id"], ["goal_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_goal_execution_tenant_state", "tenant_id", "state"),
    )
    op.create_index(op.f("ix_goal_executions_tenant_id"), "goal_executions", ["tenant_id"], unique=False)


def downgrade() -> None:
    """Drop all orchestrator tables in reverse order."""
    op.drop_index(op.f("ix_goal_executions_tenant_id"), table_name="goal_executions")
    op.drop_table("goal_executions")
    op.drop_index(op.f("ix_goal_definitions_tenant_id"), table_name="goal_definitions")
    op.drop_table("goal_definitions")
    op.drop_index(op.f("ix_agent_conflicts_tenant_id"), table_name="agent_conflicts")
    op.drop_table("agent_conflicts")
    op.drop_index(op.f("ix_agent_tasks_status"), table_name="agent_tasks")
    op.drop_index(op.f("ix_agent_tasks_tenant_id"), table_name="agent_tasks")
    op.drop_table("agent_tasks")
    op.drop_index(op.f("ix_agent_instances_definition_id"), table_name="agent_instances")
    op.drop_index(op.f("ix_agent_instances_tenant_id"), table_name="agent_instances")
    op.drop_table("agent_instances")
    op.drop_index(op.f("ix_agent_definitions_priority"), table_name="agent_definitions")
    op.drop_index(op.f("ix_agent_definitions_enabled"), table_name="agent_definitions")
    op.drop_index(op.f("ix_agent_definitions_tenant_id"), table_name="agent_definitions")
    op.drop_table("agent_definitions")
