"""Both legs at once: a deal runs as accepted until both receipts settle it, and its legs
have no due dates (QUESTIONS H1, H2; ADR-0024).

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-22 12:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SIX = "'proposed', 'accepted', 'disputed', 'settled', 'cancelled', 'expired'"
NINE = (
    "'proposed', 'accepted', 'leg1_sent', 'leg1_received', 'leg2_sent', 'disputed',"
    " 'settled', 'cancelled', 'expired'"
)


def upgrade() -> None:
    # A deal half way through the old order is simply accepted now: its legs keep their
    # marks. The journal records the move, as its trigger requires (ADR-0018).
    op.execute(
        """
        INSERT INTO events (deal_id, actor_id, type, payload)
        SELECT id, NULL, 'legs_at_once', jsonb_build_object('from', status, 'to', 'accepted')
        FROM deals WHERE status IN ('leg1_sent', 'leg1_received', 'leg2_sent')
        """
    )
    op.execute(
        """
        UPDATE deals SET status = 'accepted', last_event_id = (
            SELECT max(e.id) FROM events e
            WHERE e.deal_id = deals.id AND e.type = 'legs_at_once'
        )
        WHERE status IN ('leg1_sent', 'leg1_received', 'leg2_sent')
        """
    )
    op.drop_constraint(op.f("ck_deals_status"), "deals", type_="check")
    op.create_check_constraint(op.f("ck_deals_status"), "deals", f"status IN ({SIX})")
    op.alter_column("deal_legs", "due_date", existing_type=sa.Date(), nullable=True)


def downgrade() -> None:
    # Older code wants a date: the day the deal was proposed stands in for one.
    op.execute(
        """
        UPDATE deal_legs SET due_date = (
            SELECT created_at::date FROM deals WHERE deals.id = deal_legs.deal_id
        )
        WHERE due_date IS NULL
        """
    )
    op.alter_column("deal_legs", "due_date", existing_type=sa.Date(), nullable=False)
    op.drop_constraint(op.f("ck_deals_status"), "deals", type_="check")
    op.create_check_constraint(op.f("ck_deals_status"), "deals", f"status IN ({NINE})")
