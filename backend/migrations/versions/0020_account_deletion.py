"""Deleted accounts: the row stays, scrubbed, without its Telegram id (QUESTIONS K2,
Q-B10; ADR-0032).

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-22 22:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    # Older code wants an id: deleted accounts get negative ones, which Telegram never uses.
    op.execute(
        """
        UPDATE users SET telegram_id = -gone.n
        FROM (SELECT id, row_number() OVER (ORDER BY created_at) AS n
              FROM users WHERE telegram_id IS NULL) AS gone
        WHERE users.id = gone.id
        """
    )
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=False)
    op.drop_column("users", "deleted_at")
