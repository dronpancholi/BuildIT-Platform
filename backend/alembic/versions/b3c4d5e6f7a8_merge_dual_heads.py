"""merge dual heads

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f7, a2b3c4d5e6f7
Create Date: 2026-05-30 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = ("a1b2c3d4e5f7", "a2b3c4d5e6f7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
