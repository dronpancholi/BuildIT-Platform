"""i17_create_provider_keys_table

Phase 1.4.1 — Root Cause Recovery.

The ProviderKey ORM model exists in seo_platform.models.provider_key but
the corresponding table was never created. This blocks:
  - GET  /api/v1/providers/keys
  - PUT  /api/v1/providers/keys/{provider}
  - DELETE /api/v1/providers/keys/{provider}
  - The "needs-key" state in /providers/unified (always shows false)

Root cause: missing Alembic migration. The model was added but no
`alembic revision --autogenerate` was run before the deployment.

This migration creates the table exactly as the ORM model declares it.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


revision: str = "i17_create_provider_keys_table"
down_revision: Union[str, None] = "i16_add_updated_at_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_keys",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", PG_UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "provider", name="uq_provider_keys_tenant_provider"),
    )
    op.create_index("ix_provider_keys_tenant_id", "provider_keys", ["tenant_id"])
    op.create_index("ix_provider_keys_provider", "provider_keys", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_provider_keys_provider", table_name="provider_keys")
    op.drop_index("ix_provider_keys_tenant_id", table_name="provider_keys")
    op.drop_table("provider_keys")
