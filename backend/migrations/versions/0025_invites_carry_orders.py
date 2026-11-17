"""An invite may carry an order its author shares: `invites.order_id` (QUESTIONS O1;
ADR-0041).

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-17 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("invites", sa.Column("order_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_invites_order_id_orders"),
        "invites",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_invites_order_id"), "invites", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_invites_order_id"), table_name="invites")
    op.drop_constraint(op.f("fk_invites_order_id_orders"), "invites", type_="foreignkey")
    op.drop_column("invites", "order_id")
