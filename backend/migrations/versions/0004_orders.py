"""Orders: what each person gives and wants, who may see it, and their time zone (ADR-0016).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22 02:17:42.692193
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("give_currency", sa.String(length=8), nullable=False),
        sa.Column("give_country", sa.CHAR(length=2), nullable=False),
        sa.Column("amount_min", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("amount_max", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("amount_remaining", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("available_from", sa.Date(), nullable=False),
        sa.Column("available_until", sa.Date(), nullable=False),
        sa.Column("payout_methods", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("rate_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), server_default="open", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cardinality(payout_methods) > 0 AND payout_methods"
            " <@ ARRAY['card', 'phone', 'bank', 'crypto', 'cash', 'other']::text[]",
            name=op.f("ck_orders_payout_methods"),
        ),
        sa.CheckConstraint("give_country ~ '^[A-Z]{2}$'", name=op.f("ck_orders_give_country")),
        sa.CheckConstraint("give_currency ~ '^[A-Z]{3,5}$'", name=op.f("ck_orders_give_currency")),
        sa.CheckConstraint(
            "rate_spec->>'type' IN ('fixed', 'reference')", name=op.f("ck_orders_rate_spec_type")
        ),
        sa.CheckConstraint(
            "status IN ('open', 'fulfilled', 'closed', 'expired')", name=op.f("ck_orders_status")
        ),
        sa.CheckConstraint(
            "amount_min > 0 AND amount_min <= amount_max", name=op.f("ck_orders_amounts")
        ),
        sa.CheckConstraint(
            "amount_remaining >= 0 AND amount_remaining <= amount_max",
            name=op.f("ck_orders_remaining"),
        ),
        sa.CheckConstraint("available_from <= available_until", name=op.f("ck_orders_window")),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_orders_author_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
    )
    op.create_index(op.f("ix_orders_author_id"), "orders", ["author_id"], unique=False)
    op.create_index(
        "ix_orders_open_until",
        "orders",
        ["available_until"],
        unique=False,
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_table(
        "order_visibility",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_visibility_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_order_visibility_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("order_id", "user_id", name=op.f("pk_order_visibility")),
    )
    op.create_index(
        op.f("ix_order_visibility_user_id"), "order_visibility", ["user_id"], unique=False
    )
    op.create_table(
        "order_wants",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("country", sa.CHAR(length=2), nullable=False),
        sa.Column("position", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("country ~ '^[A-Z]{2}$'", name=op.f("ck_order_wants_country")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3,5}$'", name=op.f("ck_order_wants_currency")),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_wants_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("order_id", "currency", "country", name=op.f("pk_order_wants")),
    )
    op.add_column("users", sa.Column("tz", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "tz")
    op.drop_table("order_wants")
    op.drop_index(op.f("ix_order_visibility_user_id"), table_name="order_visibility")
    op.drop_table("order_visibility")
    op.drop_index(
        "ix_orders_open_until", table_name="orders", postgresql_where=sa.text("status = 'open'")
    )
    op.drop_index(op.f("ix_orders_author_id"), table_name="orders")
    op.drop_table("orders")
