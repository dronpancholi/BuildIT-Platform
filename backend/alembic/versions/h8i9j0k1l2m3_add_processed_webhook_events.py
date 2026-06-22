"""add_processed_webhook_events

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-06-02 11:30:00.000000

Adds ``processed_webhook_events`` table for webhook de-duplication.

Without this table, the ``/webhooks/email/{mailgun,resend,generic}``
endpoints can re-process the same provider event on every retry
(double Kafka emit, double Temporal signal, double status update).
The format-agnostic ``/webhooks/inbound/email`` already dedups via
``AuditLog.metadata_.message_id`` lookup; this table covers the
provider-specific surfaces that don't write to ``AuditLog``.

Constraint: UNIQUE (provider, event_id) is what makes dedup work
under concurrent retries. Postgres raises ``UniqueViolationError``
when the same event_id arrives twice for the same provider.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str, None], None] = None
depends_on: Union[str, Sequence[str, None], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_webhook_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider VARCHAR(50) NOT NULL,
            event_id VARCHAR(500) NOT NULL,
            tenant_id UUID,
            thread_id VARCHAR(255),
            event_type VARCHAR(50),
            processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_processed_webhook_events_provider_event
                UNIQUE (provider, event_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_processed_webhook_events_provider ON processed_webhook_events(provider)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_processed_webhook_events_tenant ON processed_webhook_events(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_processed_webhook_events_processed_at ON processed_webhook_events(processed_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_processed_webhook_events_processed_at")
    op.execute("DROP INDEX IF EXISTS ix_processed_webhook_events_tenant")
    op.execute("DROP INDEX IF EXISTS ix_processed_webhook_events_provider")
    op.execute("DROP TABLE IF EXISTS processed_webhook_events")
