"""The migrated schema agrees with the code (ADR-0002)."""

import re
from enum import StrEnum

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from swap.models import DealStatus, LinkStatus, NotificationStatus, OrderStatus, PaymentKind

# Each status CHECK, and the enum the code uses for the same column.
STATUS_CHECKS: list[tuple[str, type[StrEnum]]] = [
    ("ck_links_status", LinkStatus),
    ("ck_notifications_tg_status", NotificationStatus),
    ("ck_orders_status", OrderStatus),
    ("ck_orders_payout_methods", PaymentKind),
    ("ck_payment_methods_kind", PaymentKind),
    ("ck_deals_status", DealStatus),
    ("ck_deal_legs_method", PaymentKind),
]


@pytest.mark.parametrize(("constraint", "enum"), STATUS_CHECKS)
async def test_a_status_check_allows_exactly_its_enums_values(
    connection: AsyncConnection, constraint: str, enum: type[StrEnum]
) -> None:
    definition = await connection.scalar(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"),
        {"name": constraint},
    )
    assert definition is not None, constraint
    assert set(re.findall(r"'([^']*)'", definition)) == {member.value for member in enum}
