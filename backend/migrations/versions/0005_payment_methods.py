"""Saved payment details: free text per asset, sealed before it is stored (ADR-0010, ADR-0004).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-22 02:45:00.124892
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
            "kind IN ('card', 'phone', 'bank', 'crypto', 'cash', 'other')",
            name=op.f("ck_payment_methods_kind"),
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


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_methods_user_id"), table_name="payment_methods")
    op.drop_table("payment_methods")
