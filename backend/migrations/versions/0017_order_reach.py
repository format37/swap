"""How far an order reaches, in handshakes over active links (QUESTIONS J2; ADR-0028).

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-22 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("reach", sa.SmallInteger()))
    # Orders published so far keep what they had: their list, or the author's links.
    op.execute(
        """
        UPDATE orders SET reach = CASE
            WHEN EXISTS (SELECT 1 FROM order_visibility v WHERE v.order_id = orders.id) THEN 0
            ELSE 1
        END
        """
    )
    op.create_check_constraint(
        op.f("ck_orders_reach"), "orders", "reach IS NULL OR reach BETWEEN 0 AND 3"
    )


def downgrade() -> None:
    # Older code reads a list as "these people" and no list as "all links".
    op.drop_constraint(op.f("ck_orders_reach"), "orders", type_="check")
    op.drop_column("orders", "reach")
