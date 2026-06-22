"""add_phase12d_executive_tables

Revision ID: 1a2b3c4d5e6f
Revises: 0fc31328153b
Create Date: 2026-05-26 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, None] = '0fc31328153b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Revenue metrics — MRR, ARR, LTV tracking
    op.create_table('revenue_metrics',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('metric_date', sa.Date(), nullable=False),
        sa.Column('mrr', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('arr', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('revenue_growth_pct', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('customer_lifetime_value', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('expansion_revenue', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('churn_risk_pct', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('revenue_forecast', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('new_customers', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('churned_customers', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_customers', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('active_campaigns', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'metric_date', name='uq_revenue_metrics_date')
    )
    op.create_index(op.f('ix_revenue_metrics_tenant_id'), 'revenue_metrics', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_revenue_metrics_metric_date'), 'revenue_metrics', ['metric_date'], unique=False)

    # Customer health scores — per-client health with component breakdown
    op.create_table('customer_health_scores',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('health_score', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('health_category', sa.String(length=20), server_default=sa.text("'watch'"), nullable=False),
        sa.Column('campaign_health_avg', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('response_rate', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('delivery_rate', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('growth_velocity', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('approval_backlog', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('customer_activity_days', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('issue_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('trend_direction', sa.String(length=10), server_default=sa.text("'stable'"), nullable=False),
        sa.Column('snapshot_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'client_id', name='uq_customer_health_client')
    )
    op.create_index(op.f('ix_customer_health_tenant_id'), 'customer_health_scores', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_customer_health_client_id'), 'customer_health_scores', ['client_id'], unique=False)
    op.create_index(op.f('ix_customer_health_category'), 'customer_health_scores', ['health_category'], unique=False)

    # Risk records — detected operational risks
    op.create_table('risk_records',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('risk_type', sa.String(length=50), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('entity_name', sa.String(length=255), nullable=True),
        sa.Column('customer_name', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('acknowledged_by', sa.String(length=255), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_records_tenant_id'), 'risk_records', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_risk_records_risk_type'), 'risk_records', ['risk_type'], unique=False)
    op.create_index(op.f('ix_risk_records_risk_level'), 'risk_records', ['risk_level'], unique=False)
    op.create_index(op.f('ix_risk_records_status'), 'risk_records', ['status'], unique=False)
    op.create_index(op.f('ix_risk_records_entity_id'), 'risk_records', ['entity_id'], unique=False)

    # Executive alerts — unified alert system
    op.create_table('executive_alerts',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('entity_name', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'open'"), nullable=False),
        sa.Column('assigned_to', sa.String(length=255), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('dismissed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_executive_alerts_tenant_id'), 'executive_alerts', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_executive_alerts_source'), 'executive_alerts', ['source'], unique=False)
    op.create_index(op.f('ix_executive_alerts_severity'), 'executive_alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_executive_alerts_status'), 'executive_alerts', ['status'], unique=False)
    op.create_index(op.f('ix_executive_alerts_entity_id'), 'executive_alerts', ['entity_id'], unique=False)

    # Executive reports — persisted report records
    op.create_table('executive_reports',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('report_type', sa.String(length=20), nullable=False),
        sa.Column('period', sa.String(length=10), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('kpis', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('risks', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('opportunities', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('report_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_executive_reports_tenant_id'), 'executive_reports', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_executive_reports_report_type'), 'executive_reports', ['report_type'], unique=False)
    op.create_index(op.f('ix_executive_reports_period'), 'executive_reports', ['period'], unique=False)
    op.create_index(op.f('ix_executive_reports_generated_at'), 'executive_reports', ['generated_at'], unique=False)

    # SLA tracking
    op.create_table('sla_tracking',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('sla_type', sa.String(length=30), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('entity_name', sa.String(length=255), nullable=True),
        sa.Column('sla_target_hours', sa.Float(), nullable=False),
        sa.Column('elapsed_hours', sa.Float(), nullable=False),
        sa.Column('remaining_hours', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column('breached', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('breached_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('warning_sent', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('warning_at_pct', sa.Float(), server_default=sa.text('0.8'), nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sla_tracking_tenant_id'), 'sla_tracking', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_sla_tracking_sla_type'), 'sla_tracking', ['sla_type'], unique=False)
    op.create_index(op.f('ix_sla_tracking_status'), 'sla_tracking', ['status'], unique=False)
    op.create_index(op.f('ix_sla_tracking_breached'), 'sla_tracking', ['breached'], unique=False)

    # Executive metrics snapshots — daily KPI snapshots
    op.create_table('executive_metrics_snapshots',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('total_customers', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('active_customers', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_campaigns', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('active_campaigns', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_emails_sent', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_replies', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_links_acquired', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('avg_campaign_health', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('avg_customer_health', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('open_risks', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('pending_approvals', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('mrr', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('arr', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_prospects', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('avg_reply_rate', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('avg_acquisition_rate', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('snapshot_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'snapshot_date', name='uq_exec_metrics_date')
    )
    op.create_index(op.f('ix_exec_metrics_snapshots_tenant_id'), 'executive_metrics_snapshots', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_exec_metrics_snapshots_date'), 'executive_metrics_snapshots', ['snapshot_date'], unique=False)
    op.create_index(op.f('ix_exec_metrics_snapshots_active_campaigns'), 'executive_metrics_snapshots', ['active_campaigns'], unique=False)


def downgrade() -> None:
    op.drop_table('executive_metrics_snapshots')
    op.drop_table('sla_tracking')
    op.drop_table('executive_reports')
    op.drop_table('executive_alerts')
    op.drop_table('risk_records')
    op.drop_table('customer_health_scores')
    op.drop_table('revenue_metrics')
