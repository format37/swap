"""A rate for each wanted currency: `order_wants.rate_spec` replaces `orders.rate_spec`
(QUESTIONS J1; ADR-0026).

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-22 18:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = "rate_spec->>'type' IN ('fixed', 'reference')"


def upgrade() -> None:
    op.add_column("order_wants", sa.Column("rate_spec", postgresql.JSONB(astext_type=sa.Text())))
    # The market's spec as it was; a fixed one as its quote for this row's currency. Every
    # fixed order had one (ADR-0004), and the market stands in if one somehow didn't.
    op.execute(
        """
        UPDATE order_wants w SET rate_spec = CASE
            WHEN o.rate_spec->>'type' = 'fixed' AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(o.rate_spec->'quotes') q
                WHERE (q->>'base', q->>'quote') IN ((w.currency, o.give_currency),
                                                    (o.give_currency, w.currency))
            ) THEN jsonb_build_object('v', 1, 'type', 'fixed', 'quotes', (
                SELECT jsonb_agg(q) FROM jsonb_array_elements(o.rate_spec->'quotes') q
                WHERE (q->>'base', q->>'quote') IN ((w.currency, o.give_currency),
                                                    (o.give_currency, w.currency))
            ))
            ELSE '{"v": 1, "type": "reference", "source": "coinbase"}'::jsonb
        END
        FROM orders o WHERE o.id = w.order_id
        """
    )
    op.alter_column(
        "order_wants",
        "rate_spec",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
    )
    op.create_check_constraint(op.f("ck_order_wants_rate_spec_type"), "order_wants", KINDS)
    op.drop_constraint(op.f("ck_orders_rate_spec_type"), "orders", type_="check")
    op.drop_column("orders", "rate_spec")


def downgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("rate_spec", postgresql.JSONB(astext_type=sa.Text()), autoincrement=False),
    )
    # Older code knows one spec per order: fixed when every currency was, else the market.
    op.execute(
        """
        UPDATE orders o SET rate_spec = CASE
            WHEN NOT EXISTS (
                SELECT 1 FROM order_wants w
                WHERE w.order_id = o.id AND w.rate_spec->>'type' <> 'fixed'
            ) THEN jsonb_build_object('v', 1, 'type', 'fixed', 'quotes', (
                SELECT jsonb_agg(DISTINCT q)
                FROM order_wants w, jsonb_array_elements(w.rate_spec->'quotes') q
                WHERE w.order_id = o.id
            ))
            ELSE '{"v": 1, "type": "reference", "source": "coinbase"}'::jsonb
        END
        """
    )
    op.alter_column(
        "orders", "rate_spec", existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=False
    )
    op.create_check_constraint(op.f("ck_orders_rate_spec_type"), "orders", KINDS)
    op.drop_constraint(op.f("ck_order_wants_rate_spec_type"), "order_wants", type_="check")
    op.drop_column("order_wants", "rate_spec")
