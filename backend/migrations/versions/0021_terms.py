"""Which version of the agreement each person accepted (Q-B15, QUESTIONS K3; ADR-0033).

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-22 22:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Everyone, those already here included, accepts it at their next launch.
    op.add_column("users", sa.Column("terms_version", sa.SmallInteger()))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "terms_version")
