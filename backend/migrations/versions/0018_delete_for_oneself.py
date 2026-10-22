"""Each side deletes for themselves; a deal is erased once both have (QUESTIONS J3;
ADR-0030).

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-22 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The journal stays append-only, with one exception: a line may go once its deal has gone,
# which only erasing the whole deal does (ADR-0030). UPDATE and TRUNCATE still fail.
JOURNAL_GUARD = """
CREATE OR REPLACE FUNCTION events_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF NOT EXISTS (SELECT 1 FROM deals WHERE id = OLD.deal_id) THEN
            RETURN OLD;
        END IF;
    END IF;
    RAISE EXCEPTION 'events are append-only (ADR-0002)' USING ERRCODE = 'restrict_violation';
END
$$
"""

APPEND_ONLY = """
CREATE OR REPLACE FUNCTION events_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'events are append-only (ADR-0002)' USING ERRCODE = 'restrict_violation';
END
$$
"""


def upgrade() -> None:
    op.add_column("deals", sa.Column("proposer_deleted_at", sa.DateTime(timezone=True)))
    op.drop_constraint(op.f("fk_events_deal_id_deals"), "events", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_events_deal_id_deals"), "events", "deals", ["deal_id"], ["id"], ondelete="CASCADE"
    )
    op.execute(JOURNAL_GUARD)


def downgrade() -> None:
    op.execute(APPEND_ONLY)
    op.drop_constraint(op.f("fk_events_deal_id_deals"), "events", type_="foreignkey")
    op.create_foreign_key(op.f("fk_events_deal_id_deals"), "events", "deals", ["deal_id"], ["id"])
    op.drop_column("deals", "proposer_deleted_at")
