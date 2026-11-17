"""Payment details, sealed: on each wanted currency of an order and on each leg of a deal
(QUESTIONS Q1; ADR-0043).

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-17 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "order_wants",
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "deal_legs",
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("deal_legs", "details")
    op.drop_column("order_wants", "details")
