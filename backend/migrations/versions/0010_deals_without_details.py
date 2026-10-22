"""Deals without payment details, and with the proposer's note (QUESTIONS G1, G3; ADR-0021).

No production deal held details when they went: the parties settle where to pay
themselves.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-22 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("note", sa.Text(), nullable=True))
    op.drop_column("deal_legs", "recipient_details")
    op.drop_column("deal_legs", "recipient_title")


def downgrade() -> None:
    op.add_column("deal_legs", sa.Column("recipient_title", sa.Text(), nullable=True))
    op.add_column(
        "deal_legs",
        sa.Column("recipient_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.drop_column("deals", "note")
