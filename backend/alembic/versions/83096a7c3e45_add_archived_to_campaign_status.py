"""add_archived_to_campaign_status

Revision ID: 83096a7c3e45
Revises: s5bfix0001_extend_campaignstatus
Create Date: 2026-06-22 01:28:11.813434
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '83096a7c3e45'
down_revision: Union[str, None] = 's5bfix0001_extend_campaignstatus'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'archived'")


def downgrade() -> None:
    raise NotImplementedError(
        "PostgreSQL cannot drop a single enum value in place."
    )

