"""Three ways to pay: cash, bank, crypto (QUESTIONS G3; ADR-0021).

A card, a phone transfer (SBP) and «other» all move money between accounts, so they
become bank, in orders, deals and saved entries alike.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-22 10:40:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

THREE = ("cash", "bank", "crypto")
SIX = ("card", "phone", "bank", "crypto", "cash", "other")


def _checks(kinds: tuple[str, ...]) -> None:
    listed = ", ".join(f"'{kind}'" for kind in kinds)
    for column in ("payout_methods", "receive_methods"):
        op.create_check_constraint(
            op.f(f"ck_orders_{column}"),
            "orders",
            f"cardinality({column}) > 0 AND {column} <@ ARRAY[{listed}]::text[]",
        )
    op.create_check_constraint(op.f("ck_deal_legs_method"), "deal_legs", f"method IN ({listed})")
    op.create_check_constraint(
        op.f("ck_payment_methods_kind"), "payment_methods", f"kind IN ({listed})"
    )


def _drop_checks() -> None:
    for name, table in (
        ("ck_orders_payout_methods", "orders"),
        ("ck_orders_receive_methods", "orders"),
        ("ck_deal_legs_method", "deal_legs"),
        ("ck_payment_methods_kind", "payment_methods"),
    ):
        op.drop_constraint(op.f(name), table, type_="check")


def upgrade() -> None:
    _drop_checks()
    # Each list keeps one of each, in the order the app shows them.
    for column in ("payout_methods", "receive_methods"):
        op.execute(
            f"""
            UPDATE orders SET {column} = ARRAY(
                SELECT way FROM (
                    SELECT DISTINCT CASE WHEN kind IN ('card', 'phone', 'other')
                        THEN 'bank' ELSE kind END AS way
                    FROM unnest({column}) AS kind
                ) AS ways
                ORDER BY array_position(ARRAY['cash', 'bank', 'crypto'], way)
            )
            """  # noqa: S608 - the column names are ours, not input
        )
    op.execute("UPDATE deal_legs SET method = 'bank' WHERE method IN ('card', 'phone', 'other')")
    op.execute("UPDATE payment_methods SET kind = 'bank' WHERE kind IN ('card', 'phone', 'other')")
    _checks(THREE)


def downgrade() -> None:
    # Three fit within six, so the rows need no change.
    _drop_checks()
    _checks(SIX)
