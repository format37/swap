"""Orders may have no minimum and no last day (QUESTIONS F3, F4; ADR-0019).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-22 08:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_orders_amounts"), "orders", type_="check")
    op.create_check_constraint(
        op.f("ck_orders_amounts"), "orders", "amount_min >= 0 AND amount_min <= amount_max"
    )
    op.alter_column("orders", "available_until", existing_type=sa.Date(), nullable=True)


def downgrade() -> None:
    # The old rules, as Q-B5 and Q-B17 had them: the smallest deal is a cent, and an
    # order without a last day gets the two weeks the wizard used to offer.
    op.execute("UPDATE orders SET amount_min = 0.01 WHERE amount_min = 0")
    op.execute(
        "UPDATE orders SET available_until = available_from + 14 WHERE available_until IS NULL"
    )
    op.alter_column("orders", "available_until", existing_type=sa.Date(), nullable=False)
    op.drop_constraint(op.f("ck_orders_amounts"), "orders", type_="check")
    op.create_check_constraint(
        op.f("ck_orders_amounts"), "orders", "amount_min > 0 AND amount_min <= amount_max"
    )
