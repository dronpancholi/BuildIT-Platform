"""extend campaignstatus enum with fail-loud guard states (Phase S5B-FIX)

This migration extends the PostgreSQL ``campaignstatus`` enum to include
the ``failed_no_prospects`` and ``failed_no_emails_sent`` values that the
``BacklinkCampaignWorkflow`` writes via ``update_campaign_status_activity``
at its fail-loud guards (see ``seo_platform/workflows/backlink_campaign.py``
lines 1229 and 1452).

Without these values the existing activity raises ``ValueError`` because
``CampaignStatus(status)`` cannot coerce the unknown string; this activity
was registered with ``RetryPreset.DATABASE`` so the activity retries
indefinitely, the workflow run is evicted, and **no prospect rows persist**.

PostgreSQL enum-value lifecycle note
------------------------------------
PostgreSQL ≥ 10 accepts ``ALTER TYPE ... ADD VALUE`` inside a normal
transaction; pre-PG-10 and some PG-13+ configurations require it to run
in autocommit mode. Since this project runs PG ≥ 13 by current minimum,
the standard ``op.execute`` path inside this migration's transaction is
sufficient. For an older target PG, swap in ``op.get_context().autocommit_block()``.

Idempotency
-----------
- ``ADD VALUE IF NOT EXISTS``: native idempotent in PG ≥ 9.6.

Revision ID: s5bfix0001_extend_campaignstatus
Revises:    8efe6a0f6459
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "s5bfix0001_extend_campaignstatus"
down_revision = "8efe6a0f6459"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add two campaign_status enum values (idempotent).

    PG type name is ``campaign_status`` (Postgres converts CamelCase by
    convention to snake_case). The Python ``CampaignStatus`` enum lives at
    ``seo_platform/models/backlink.py`` and serialises using its ``str``
    values, which are the same strings stored in the PG type.
    """
    op.execute("ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'failed_no_prospects'")
    op.execute("ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'failed_no_emails_sent'")


def downgrade() -> None:
    """Drop two campaignstatus enum values.

    PostgreSQL does not support ``ALTER TYPE ... DROP VALUE`` directly;
    use the manual rename-and-recreate procedure if needed:

        ALTER TYPE campaignstatus RENAME TO campaignstatus_old;
        CREATE TYPE campaignstatus AS ENUM (
            'draft','prospecting','scoring','outreach_prep',
            'awaiting_approval','active','paused','monitoring',
            'complete','cancelled','archived'
        );
        ALTER TABLE backlink_campaigns
            ALTER COLUMN status DROP DEFAULT,
            ALTER COLUMN status TYPE campaignstatus USING status::text::campaignstatus;
        DROP TYPE campaignstatus_old;
    """
    raise NotImplementedError(
        "PostgreSQL cannot drop a single enum value in place; "
        "use the manual rename-and-recreate procedure documented in the docstring."
    )
