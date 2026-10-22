"""A link to each user's Telegram photo (QUESTIONS J4; ADR-0027).

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-22 19:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Filled at each person's next sign-in.
    op.add_column("users", sa.Column("photo_url", sa.Text()))


def downgrade() -> None:
    op.drop_column("users", "photo_url")
