"""«№ 17»: a number for every order, from one sequence (QUESTIONS K8; ADR-0034).

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-22 23:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE order_numbers")
    op.add_column("orders", sa.Column("number", sa.BigInteger()))
    # The orders so far, numbered in the order they were published.
    op.execute(
        """
        UPDATE orders SET number = numbered.n
        FROM (SELECT id, row_number() OVER (ORDER BY created_at, id) AS n FROM orders) AS numbered
        WHERE orders.id = numbered.id
        """
    )
    op.execute("SELECT setval('order_numbers', coalesce(max(number), 0) + 1, false) FROM orders")
    op.alter_column(
        "orders",
        "number",
        existing_type=sa.BigInteger(),
        nullable=False,
        server_default=sa.text("nextval('order_numbers')"),
    )
    op.create_unique_constraint(op.f("uq_orders_number"), "orders", ["number"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_orders_number"), "orders", type_="unique")
    op.drop_column("orders", "number")
    op.execute("DROP SEQUENCE order_numbers")
