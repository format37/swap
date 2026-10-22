"""Recurring orders: a monthly copy on day N, once per month (QUESTIONS K7; ADR-0036).

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-22 23:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("repeat_day", sa.SmallInteger()))
    op.add_column("orders", sa.Column("series_id", sa.Uuid()))
    op.add_column("orders", sa.Column("series_month", sa.Date()))
    op.create_check_constraint(
        op.f("ck_orders_repeat_day"), "orders", "repeat_day IS NULL OR repeat_day BETWEEN 1 AND 31"
    )
    # One order per series and month: what keeps the monthly job from publishing twice.
    op.create_unique_constraint(
        op.f("uq_orders_series_id_series_month"), "orders", ["series_id", "series_month"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_orders_series_id_series_month"), "orders", type_="unique")
    op.drop_constraint(op.f("ck_orders_repeat_day"), "orders", type_="check")
    op.drop_column("orders", "series_month")
    op.drop_column("orders", "series_id")
    op.drop_column("orders", "repeat_day")
