"""add_critical_foreign_keys

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-30 10:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # keywords.client_id → clients.id
    op.create_foreign_key(
        "fk_keywords_client_id",
        "keywords",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # keywords.cluster_id → keyword_clusters.id
    op.create_foreign_key(
        "fk_keywords_cluster_id",
        "keywords",
        "keyword_clusters",
        ["cluster_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # backlink_campaigns.client_id → clients.id
    op.create_foreign_key(
        "fk_backlink_campaigns_client_id",
        "backlink_campaigns",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # backlink_prospects.campaign_id → backlink_campaigns.id
    op.create_foreign_key(
        "fk_backlink_prospects_campaign_id",
        "backlink_prospects",
        "backlink_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # outreach_threads.campaign_id → backlink_campaigns.id
    op.create_foreign_key(
        "fk_outreach_threads_campaign_id",
        "outreach_threads",
        "backlink_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # outreach_threads.prospect_id → backlink_prospects.id
    op.create_foreign_key(
        "fk_outreach_threads_prospect_id",
        "outreach_threads",
        "backlink_prospects",
        ["prospect_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # acquired_links.campaign_id → backlink_campaigns.id
    op.create_foreign_key(
        "fk_acquired_links_campaign_id",
        "acquired_links",
        "backlink_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # acquired_links.prospect_id → backlink_prospects.id
    op.create_foreign_key(
        "fk_acquired_links_prospect_id",
        "acquired_links",
        "backlink_prospects",
        ["prospect_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # reports.client_id → clients.id
    op.create_foreign_key(
        "fk_reports_client_id",
        "reports",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # reports.campaign_id → backlink_campaigns.id
    op.create_foreign_key(
        "fk_reports_campaign_id",
        "reports",
        "backlink_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # campaign_health_snapshots.campaign_id → backlink_campaigns.id
    op.create_foreign_key(
        "fk_campaign_health_snapshots_campaign_id",
        "campaign_health_snapshots",
        "backlink_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # campaign_timeline_events.campaign_id → backlink_campaigns.id
    op.create_foreign_key(
        "fk_campaign_timeline_events_campaign_id",
        "campaign_timeline_events",
        "backlink_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_campaign_timeline_events_campaign_id", "campaign_timeline_events", type_="foreignkey")
    op.drop_constraint("fk_campaign_health_snapshots_campaign_id", "campaign_health_snapshots", type_="foreignkey")
    op.drop_constraint("fk_reports_campaign_id", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_client_id", "reports", type_="foreignkey")
    op.drop_constraint("fk_acquired_links_prospect_id", "acquired_links", type_="foreignkey")
    op.drop_constraint("fk_acquired_links_campaign_id", "acquired_links", type_="foreignkey")
    op.drop_constraint("fk_outreach_threads_prospect_id", "outreach_threads", type_="foreignkey")
    op.drop_constraint("fk_outreach_threads_campaign_id", "outreach_threads", type_="foreignkey")
    op.drop_constraint("fk_backlink_prospects_campaign_id", "backlink_prospects", type_="foreignkey")
    op.drop_constraint("fk_backlink_campaigns_client_id", "backlink_campaigns", type_="foreignkey")
    op.drop_constraint("fk_keywords_cluster_id", "keywords", type_="foreignkey")
    op.drop_constraint("fk_keywords_client_id", "keywords", type_="foreignkey")
