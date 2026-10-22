"""Ways to be paid for each wanted currency: `order_wants.receive_methods` replaces
`orders.receive_methods` (QUESTIONS L1; ADR-0037).

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-23 00:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = (
    "cardinality(receive_methods) > 0"
    " AND receive_methods <@ ARRAY['cash', 'bank', 'crypto']::text[]"
)


def upgrade() -> None:
    op.add_column("order_wants", sa.Column("receive_methods", postgresql.ARRAY(sa.Text())))
    # Every currency of an order takes what the whole order took until now.
    op.execute(
        "UPDATE order_wants w SET receive_methods = o.receive_methods"
        " FROM orders o WHERE o.id = w.order_id"
    )
    op.alter_column(
        "order_wants", "receive_methods", existing_type=postgresql.ARRAY(sa.Text()), nullable=False
    )
    op.create_check_constraint(op.f("ck_order_wants_receive_methods"), "order_wants", KINDS)
    op.drop_constraint(op.f("ck_orders_receive_methods"), "orders", type_="check")
    op.drop_column("orders", "receive_methods")


def downgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("receive_methods", postgresql.ARRAY(sa.Text()), autoincrement=False),
    )
    # Older code knows one set per order: every way any of its currencies took.
    op.execute(
        """
        UPDATE orders o SET receive_methods = ARRAY(
            SELECT kind FROM (
                SELECT DISTINCT unnest(w.receive_methods) AS kind
                FROM order_wants w WHERE w.order_id = o.id
            ) taken
            ORDER BY array_position(ARRAY['cash', 'bank', 'crypto'], kind)
        )
        """
    )
    op.alter_column(
        "orders", "receive_methods", existing_type=postgresql.ARRAY(sa.Text()), nullable=False
    )
    op.create_check_constraint(op.f("ck_orders_receive_methods"), "orders", KINDS)
    op.drop_constraint(op.f("ck_order_wants_receive_methods"), "order_wants", type_="check")
    op.drop_column("order_wants", "receive_methods")
