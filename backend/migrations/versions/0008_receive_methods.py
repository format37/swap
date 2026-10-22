"""How an order's author can be paid (QUESTIONS F2; ADR-0019).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-22 09:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("receive_methods", postgresql.ARRAY(sa.Text())))
    # Until now a proposal could pay in any way, so that is what older orders accept.
    op.execute(
        "UPDATE orders"
        " SET receive_methods = ARRAY['card', 'phone', 'bank', 'crypto', 'cash', 'other']"
    )
    op.alter_column(
        "orders", "receive_methods", existing_type=postgresql.ARRAY(sa.Text()), nullable=False
    )
    op.create_check_constraint(
        op.f("ck_orders_receive_methods"),
        "orders",
        "cardinality(receive_methods) > 0 AND receive_methods"
        " <@ ARRAY['card', 'phone', 'bank', 'crypto', 'cash', 'other']::text[]",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_orders_receive_methods"), "orders", type_="check")
    op.drop_column("orders", "receive_methods")
