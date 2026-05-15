"""add domain tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enums ---
    search_intent = sa.Enum("informational", "navigational", "commercial", "transactional", name="search_intent", create_constraint=True)
    cluster_status = sa.Enum("draft", "pending_approval", "approved", "rejected", "archived", name="cluster_status", create_constraint=True)
    campaign_type = sa.Enum("guest_post", "resource_page", "niche_edit", "broken_link", "skyscraper", "haro", name="campaign_type", create_constraint=True)
    campaign_status = sa.Enum("draft", "prospecting", "scoring", "outreach_prep", "awaiting_approval", "active", "paused", "monitoring", "complete", "cancelled", name="campaign_status", create_constraint=True)
    prospect_status = sa.Enum("new", "scored", "approved", "rejected", "outreach_queued", "contacted", "replied", "link_acquired", "link_lost", "unresponsive", name="prospect_status", create_constraint=True)
    thread_status = sa.Enum("draft", "queued", "sent", "delivered", "opened", "replied", "bounced", "spam_reported", "unsubscribed", "link_acquired", name="thread_status", create_constraint=True)
    link_status = sa.Enum("pending_verification", "verified_live", "verified_nofollow", "removed", "broken", name="link_status", create_constraint=True)
    approval_category = sa.Enum("campaign_launch", "outreach_templates", "keyword_clusters", "prospect_list", "budget_override", "rule_change", name="approval_category", create_constraint=True)
    risk_level = sa.Enum("low", "medium", "high", "critical", name="risk_level", create_constraint=True)
    approval_status = sa.Enum("pending", "approved", "rejected", "modification_requested", "expired", "delegated", name="approval_status", create_constraint=True)

    # --- Keyword Clusters ---
    op.create_table(
        "keyword_clusters",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("primary_keyword", sa.String(500), nullable=False),
        sa.Column("total_volume", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_difficulty", sa.Float, nullable=False, server_default="0"),
        sa.Column("dominant_intent", search_intent, nullable=True),
        sa.Column("keyword_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("status", cluster_status, nullable=False, server_default="draft"),
        sa.Column("ai_rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Keywords ---
    op.create_table(
        "keywords",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("cluster_id", UUID(as_uuid=True), sa.ForeignKey("keyword_clusters.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("keyword", sa.String(500), nullable=False),
        sa.Column("search_volume", sa.Integer, nullable=False, server_default="0"),
        sa.Column("difficulty", sa.Float, nullable=False, server_default="0"),
        sa.Column("cpc", sa.Float, nullable=False, server_default="0"),
        sa.Column("competition", sa.Float, nullable=False, server_default="0"),
        sa.Column("intent", search_intent, nullable=True),
        sa.Column("serp_features", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("enrichment_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_seed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("embedding_vector_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "client_id", "keyword", name="uq_keyword_tenant_client"),
    )

    # --- Backlink Campaigns ---
    op.create_table(
        "backlink_campaigns",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("campaign_type", campaign_type, nullable=False),
        sa.Column("status", campaign_status, nullable=False, server_default="draft", index=True),
        sa.Column("target_link_count", sa.Integer, nullable=False, server_default="10"),
        sa.Column("acquired_link_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_prospects", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_emails_sent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reply_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("acquisition_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("health_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("workflow_run_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Backlink Prospects ---
    op.create_table(
        "backlink_prospects",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("backlink_campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("domain", sa.String(255), nullable=False, index=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("status", prospect_status, nullable=False, server_default="new", index=True),
        sa.Column("domain_authority", sa.Float, nullable=False, server_default="0"),
        sa.Column("relevance_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("spam_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("traffic_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("composite_score", sa.Float, nullable=False, server_default="0", index=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_source", sa.String(50), nullable=True),
        sa.Column("scoring_rationale", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("page_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "campaign_id", "domain", name="uq_prospect_campaign_domain"),
    )

    # --- Outreach Threads ---
    op.create_table(
        "outreach_threads",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("backlink_campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("prospect_id", UUID(as_uuid=True), sa.ForeignKey("backlink_prospects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", thread_status, nullable=False, server_default="draft", index=True),
        sa.Column("from_email", sa.String(255), nullable=False),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_html", sa.Text, nullable=False, server_default=""),
        sa.Column("follow_up_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_follow_ups", sa.Integer, nullable=False, server_default="3"),
        sa.Column("provider", sa.String(50), nullable=False, server_default="'sendgrid'"),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("ai_personalization", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Acquired Links ---
    op.create_table(
        "acquired_links",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("backlink_campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("prospect_id", UUID(as_uuid=True), sa.ForeignKey("backlink_prospects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("target_url", sa.String(2048), nullable=False),
        sa.Column("anchor_text", sa.String(500), nullable=False, server_default=""),
        sa.Column("link_type", sa.String(50), nullable=False, server_default="'dofollow'"),
        sa.Column("status", link_status, nullable=False, server_default="pending_verification"),
        sa.Column("domain_authority_at_acquisition", sa.Float, nullable=False, server_default="0"),
        sa.Column("first_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Approval Requests ---
    op.create_table(
        "approval_requests",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_run_id", sa.String(255), nullable=False, index=True),
        sa.Column("category", approval_category, nullable=False, index=True),
        sa.Column("risk_level", risk_level, nullable=False, index=True),
        sa.Column("status", approval_status, nullable=False, server_default="pending", index=True),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("ai_risk_summary", sa.Text, nullable=False, server_default=""),
        sa.Column("context_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to", UUID(as_uuid=True), nullable=True),
        sa.Column("decided_by", UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text, nullable=False, server_default=""),
        sa.Column("modifications", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("escalation_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- RLS for all new tenant-scoped tables ---
    rls_tables = [
        "keyword_clusters", "keywords", "backlink_campaigns",
        "backlink_prospects", "outreach_threads", "acquired_links",
        "approval_requests",
    ]
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant')::uuid)
        """)

    # --- Performance Indexes ---
    op.create_index("ix_keywords_volume", "keywords", ["search_volume"], postgresql_ops={})
    op.create_index("ix_keywords_difficulty", "keywords", ["difficulty"], postgresql_ops={})
    op.create_index("ix_prospects_composite", "backlink_prospects", ["composite_score"], postgresql_ops={})
    op.create_index("ix_threads_sent_at", "outreach_threads", ["sent_at"], postgresql_ops={})
    op.create_index("ix_approval_sla", "approval_requests", ["sla_deadline"], postgresql_ops={})
    op.create_index("ix_campaigns_status_tenant", "backlink_campaigns", ["tenant_id", "status"], postgresql_ops={})


def downgrade() -> None:
    rls_tables = [
        "approval_requests", "acquired_links", "outreach_threads",
        "backlink_prospects", "backlink_campaigns", "keywords", "keyword_clusters",
    ]
    for table in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for idx in ["ix_campaigns_status_tenant", "ix_approval_sla", "ix_threads_sent_at",
                 "ix_prospects_composite", "ix_keywords_difficulty", "ix_keywords_volume"]:
        op.drop_index(idx)

    for table in rls_tables:
        op.drop_table(table)

    for enum_name in ["approval_status", "risk_level", "approval_category", "link_status",
                       "thread_status", "prospect_status", "campaign_status", "campaign_type",
                       "cluster_status", "search_intent"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
