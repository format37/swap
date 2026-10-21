"""Deals, their two legs, and the journal, guarded in the database (ADR-0002, ADR-0018).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-22 02:55:25.028871
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The journal can only grow (ADR-0002).
EVENTS_APPEND_ONLY = (
    """
    CREATE FUNCTION events_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'events are append-only (ADR-0002)' USING ERRCODE = 'restrict_violation';
    END
    $$
    """,
    """
    CREATE TRIGGER events_append_only BEFORE UPDATE OR DELETE ON events
        FOR EACH ROW EXECUTE FUNCTION events_append_only()
    """,
    """
    CREATE TRIGGER events_no_truncate BEFORE TRUNCATE ON events
        FOR EACH STATEMENT EXECUTE FUNCTION events_append_only()
    """,
)

# A deal starts as proposed, and its status changes only together with the event that
# records the change: the row must point at an event of this deal whose payload goes from
# the old status to the new one (ADR-0018). A stray UPDATE fails at once.
DEALS_JOURNALED = (
    """
    CREATE FUNCTION deals_journaled() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            IF NEW.status <> 'proposed' THEN
                RAISE EXCEPTION 'a deal starts as proposed (ADR-0018)'
                    USING ERRCODE = 'check_violation';
            END IF;
        ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
            IF NEW.last_event_id IS NOT DISTINCT FROM OLD.last_event_id OR NOT EXISTS (
                SELECT 1 FROM events
                WHERE id = NEW.last_event_id
                  AND deal_id = NEW.id
                  AND payload ->> 'from' = OLD.status
                  AND payload ->> 'to' = NEW.status
            ) THEN
                RAISE EXCEPTION 'deal % moved from % to % without its event (ADR-0018)',
                    NEW.id, OLD.status, NEW.status USING ERRCODE = 'check_violation';
            END IF;
        END IF;
        RETURN NEW;
    END
    $$
    """,
    """
    CREATE TRIGGER deals_journaled BEFORE INSERT OR UPDATE ON deals
        FOR EACH ROW EXECUTE FUNCTION deals_journaled()
    """,
)


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("proposer_id", sa.Uuid(), nullable=False),
        sa.Column("acceptor_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default="proposed", nullable=False),
        sa.Column("rate_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rate_base", sa.String(length=8), nullable=False),
        sa.Column("rate_quote", sa.String(length=8), nullable=False),
        sa.Column("rate_value", sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column("rate_locked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("whole", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_by", sa.Uuid(), nullable=True),
        sa.Column("disputed_by", sa.Uuid(), nullable=True),
        sa.Column("dispute_note", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolution_by", sa.Uuid(), nullable=True),
        sa.Column("last_event_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "resolution IS NULL OR resolution IN ('settled', 'cancelled')",
            name=op.f("ck_deals_resolution"),
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'accepted', 'leg1_sent', 'leg1_received', 'leg2_sent',"
            " 'disputed', 'settled', 'cancelled', 'expired')",
            name=op.f("ck_deals_status"),
        ),
        sa.CheckConstraint(
            "cancel_requested_by IS NULL OR cancel_requested_by IN (proposer_id, acceptor_id)",
            name=op.f("ck_deals_cancel_requested_by"),
        ),
        sa.CheckConstraint(
            "disputed_by IS NULL OR disputed_by IN (proposer_id, acceptor_id)",
            name=op.f("ck_deals_disputed_by"),
        ),
        sa.CheckConstraint("proposer_id <> acceptor_id", name=op.f("ck_deals_two_people")),
        sa.CheckConstraint(
            "resolution_by IS NULL OR resolution_by IN (proposer_id, acceptor_id)",
            name=op.f("ck_deals_resolution_by"),
        ),
        sa.ForeignKeyConstraint(
            ["acceptor_id"], ["users.id"], name=op.f("fk_deals_acceptor_id_users")
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_deals_order_id_orders")),
        sa.ForeignKeyConstraint(
            ["proposer_id"], ["users.id"], name=op.f("fk_deals_proposer_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deals")),
    )
    op.create_index(op.f("ix_deals_acceptor_id"), "deals", ["acceptor_id"], unique=False)
    op.create_index(op.f("ix_deals_order_id"), "deals", ["order_id"], unique=False)
    op.create_index(
        "ix_deals_proposed_until",
        "deals",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'proposed'"),
    )
    op.create_index(op.f("ix_deals_proposer_id"), "deals", ["proposer_id"], unique=False)
    op.create_table(
        "deal_legs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.SmallInteger(), nullable=False),
        sa.Column("payer_id", sa.Uuid(), nullable=False),
        sa.Column("payee_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("country", sa.CHAR(length=2), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("recipient_title", sa.Text(), nullable=True),
        sa.Column("recipient_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("country ~ '^[A-Z]{2}$'", name=op.f("ck_deal_legs_country")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3,5}$'", name=op.f("ck_deal_legs_currency")),
        sa.CheckConstraint(
            "method IN ('card', 'phone', 'bank', 'crypto', 'cash', 'other')",
            name=op.f("ck_deal_legs_method"),
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_deal_legs_amount")),
        sa.CheckConstraint("payer_id <> payee_id", name=op.f("ck_deal_legs_two_people")),
        sa.CheckConstraint(
            "received_at IS NULL OR sent_at IS NOT NULL", name=op.f("ck_deal_legs_sent_first")
        ),
        sa.CheckConstraint("seq IN (1, 2)", name=op.f("ck_deal_legs_seq")),
        sa.ForeignKeyConstraint(
            ["deal_id"], ["deals.id"], name=op.f("fk_deal_legs_deal_id_deals"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["payee_id"], ["users.id"], name=op.f("fk_deal_legs_payee_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["payer_id"], ["users.id"], name=op.f("fk_deal_legs_payer_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deal_legs")),
        sa.UniqueConstraint("deal_id", "seq", name=op.f("uq_deal_legs_deal_id_seq")),
    )
    op.create_index(op.f("ix_deal_legs_payee_id"), "deal_legs", ["payee_id"], unique=False)
    op.create_index(op.f("ix_deal_legs_payer_id"), "deal_legs", ["payer_id"], unique=False)
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name=op.f("fk_events_actor_id_users")),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], name=op.f("fk_events_deal_id_deals")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
    )
    op.create_index(op.f("ix_events_actor_id"), "events", ["actor_id"], unique=False)
    op.create_index(op.f("ix_events_deal_id"), "events", ["deal_id"], unique=False)
    for statement in (*EVENTS_APPEND_ONLY, *DEALS_JOURNALED):
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TRIGGER deals_journaled ON deals")
    op.execute("DROP FUNCTION deals_journaled()")
    op.execute("DROP TRIGGER events_no_truncate ON events")
    op.execute("DROP TRIGGER events_append_only ON events")
    op.execute("DROP FUNCTION events_append_only()")
    op.drop_index(op.f("ix_events_deal_id"), table_name="events")
    op.drop_index(op.f("ix_events_actor_id"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_deal_legs_payer_id"), table_name="deal_legs")
    op.drop_index(op.f("ix_deal_legs_payee_id"), table_name="deal_legs")
    op.drop_table("deal_legs")
    op.drop_index(op.f("ix_deals_proposer_id"), table_name="deals")
    op.drop_index(
        "ix_deals_proposed_until",
        table_name="deals",
        postgresql_where=sa.text("status = 'proposed'"),
    )
    op.drop_index(op.f("ix_deals_order_id"), table_name="deals")
    op.drop_index(op.f("ix_deals_acceptor_id"), table_name="deals")
    op.drop_table("deals")
