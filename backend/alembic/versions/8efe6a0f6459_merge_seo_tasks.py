"""merge seo_tasks

Revision ID: 8efe6a0f6459
Revises: k1, z1
Create Date: 2026-06-18 15:09:30.428962
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '8efe6a0f6459'
down_revision: Union[str, None] = ('k1', 'z1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
