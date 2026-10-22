"""Where a deal's market rate came from, and when (FR-3.5; QUESTIONS G2; ADR-0022).

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-22 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("rate_source", sa.Text(), nullable=True))
    op.add_column("deals", sa.Column("rate_fetched_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("deals", "rate_fetched_at")
    op.drop_column("deals", "rate_source")
