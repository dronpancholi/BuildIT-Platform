"""add_phase12e_automation_tables

Revision ID: 2a3b4c5d6e7f
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-26 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Automation rules — core rules definition
    op.create_table('automation_rules',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('trigger_type', sa.String(length=50), nullable=False),
        sa.Column('trigger_config', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('condition_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('action_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('workflow_type', sa.String(length=20), server_default=sa.text("'single'"), nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default=sa.text('3'), nullable=False),
        sa.Column('cooldown_minutes', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('success_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('failure_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_rules_tenant_id'), 'automation_rules', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_automation_rules_trigger_type'), 'automation_rules', ['trigger_type'], unique=False)
    op.create_index(op.f('ix_automation_rules_enabled'), 'automation_rules', ['enabled'], unique=False)

    # Automation runs — execution history for each rule
    op.create_table('automation_runs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=False),
        sa.Column('rule_name', sa.String(length=255), nullable=True),
        sa.Column('trigger_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('condition_result', sa.Boolean(), nullable=True),
        sa.Column('condition_details', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('result_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['automation_rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_runs_tenant_id'), 'automation_runs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_automation_runs_rule_id'), 'automation_runs', ['rule_id'], unique=False)
    op.create_index(op.f('ix_automation_runs_status'), 'automation_runs', ['status'], unique=False)
    op.create_index(op.f('ix_automation_runs_started_at'), 'automation_runs', ['started_at'], unique=False)

    # Automation actions — individual actions executed within a run
    op.create_table('automation_actions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=True),
        sa.Column('step_index', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('action_config', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['automation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_actions_tenant_id'), 'automation_actions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_automation_actions_run_id'), 'automation_actions', ['run_id'], unique=False)
    op.create_index(op.f('ix_automation_actions_action_type'), 'automation_actions', ['action_type'], unique=False)
    op.create_index(op.f('ix_automation_actions_status'), 'automation_actions', ['status'], unique=False)

    # Automation failures — failure tracking with retry support
    op.create_table('automation_failures',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=True),
        sa.Column('action_id', sa.UUID(), nullable=True),
        sa.Column('failure_type', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('error_detail', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('retry_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default=sa.text('3'), nullable=False),
        sa.Column('retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['automation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_failures_tenant_id'), 'automation_failures', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_automation_failures_run_id'), 'automation_failures', ['run_id'], unique=False)
    op.create_index(op.f('ix_automation_failures_failure_type'), 'automation_failures', ['failure_type'], unique=False)
    op.create_index(op.f('ix_automation_failures_resolved'), 'automation_failures', ['resolved'], unique=False)


def downgrade() -> None:
    op.drop_table('automation_failures')
    op.drop_table('automation_actions')
    op.drop_table('automation_runs')
    op.drop_table('automation_rules')
