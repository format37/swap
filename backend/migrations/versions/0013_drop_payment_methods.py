"""Saved payment details go, with the owner's go (QUESTIONS G7; ADR-0021).

Nothing has read them since deals stopped asking for payment details. Their four entries
were sealed with a key that goes from the server's environment as well.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-22 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_payment_methods_user_id"), table_name="payment_methods")
    op.drop_table("payment_methods")


def downgrade() -> None:
    # The table comes back empty: what it held is gone for good.
    op.create_table(
        "payment_methods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("asset", sa.String(length=8), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("asset ~ '^[A-Z]{3,5}$'", name=op.f("ck_payment_methods_asset")),
        sa.CheckConstraint(
            "kind IN ('cash', 'bank', 'crypto')", name=op.f("ck_payment_methods_kind")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_payment_methods_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_methods")),
    )
    op.create_index(
        op.f("ix_payment_methods_user_id"), "payment_methods", ["user_id"], unique=False
    )
