"""Add seo_tasks table for Phase 13 task engine

Revision ID: z1
Revises: 
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = 'z1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums only if they don't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_status AS ENUM ('created', 'assigned', 'in_progress', 'blocked', 'completed', 'cancelled');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_priority AS ENUM ('P0', 'P1', 'P2', 'P3');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_source AS ENUM ('manual', 'recommendation', 'citation_failure', 'outreach_action', 'campaign_health', 'automation', 'copilot');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)
    
    op.create_table(
        'seo_tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='created'),
        sa.Column('priority', sa.String(10), nullable=False, server_default='P1'),
        sa.Column('source', sa.String(50), nullable=False, server_default='manual'),
        sa.Column('client_id', UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=True, index=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('backlink_campaigns.id'), nullable=True, index=True),
        sa.Column('assigned_to', sa.String(200), nullable=True),
        sa.Column('owner', sa.String(200), nullable=True),
        sa.Column('source_recommendation_id', sa.String(200), nullable=True),
        sa.Column('source_entity_type', sa.String(100), nullable=True),
        sa.Column('source_entity_id', UUID(as_uuid=True), nullable=True),
        sa.Column('impact_score', sa.Integer, nullable=True),
        sa.Column('estimated_days', sa.Integer, nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completion_notes', sa.Text, nullable=True),
        sa.Column('tags', JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('metadata', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    
    op.create_index('ix_seo_tasks_tenant_status', 'seo_tasks', ['tenant_id', 'status'])
    op.create_index('ix_seo_tasks_tenant_priority', 'seo_tasks', ['tenant_id', 'priority'])
    op.create_index('ix_seo_tasks_tenant_client', 'seo_tasks', ['tenant_id', 'client_id'])
    op.create_index('ix_seo_tasks_tenant_campaign', 'seo_tasks', ['tenant_id', 'campaign_id'])


def downgrade() -> None:
    op.drop_table('seo_tasks')
    op.execute("DROP TYPE IF EXISTS task_source")
    op.execute("DROP TYPE IF EXISTS task_priority")
    op.execute("DROP TYPE IF EXISTS task_status")
