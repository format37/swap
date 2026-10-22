"""Recurring orders (QUESTIONS K7, ADR-0036): a copy on day N of every month, once.
Refusals first: nobody else stops a series, and nothing goes out before its day."""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.config import Settings
from swap.models import Notification, Order
from swap.repeats import due_day, repeat_due
from tests.test_links import ALEX, GIO, NINO, linked, person
from tests.test_orders import MARKET, fixed, publish, want

Sessions = async_sessionmaker[AsyncSession]


def next_month(day: int) -> datetime:
    """Noon on day `day` of next month, UTC."""
    first = (datetime.now(UTC).date().replace(day=1) + timedelta(days=32)).replace(day=1)
    return datetime(first.year, first.month, day, 12, tzinfo=UTC)


async def run(sessions: Sessions, settings: Settings, now: datetime) -> int:
    async with sessions() as db:
        published = await repeat_due(db, settings.assets, now)
        await db.commit()
    return published


async def series(sessions: Sessions, order: dict[str, Any]) -> list[Order]:
    async with sessions() as db:
        first = await db.get(Order, uuid.UUID(order["id"]))
        assert first is not None
        found = await db.scalars(
            select(Order).where(Order.series_id == first.series_id).order_by(Order.number)
        )
        return list(found)


# --- refused ---------------------------------------------------------------------------


async def test_nobody_else_stops_a_series_and_a_single_order_has_none(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    alex = await person(client, ALEX)
    gio = await person(client, GIO)
    order = await publish(client, alex, repeat_day=5)
    stop = f"/api/v1/orders/{order['id']}/stop-repeating"
    assert (await client.post(stop, headers=gio)).status_code == 404
    once = await publish(client, alex)
    refused = await client.post(f"/api/v1/orders/{once['id']}/stop-repeating", headers=alex)
    assert refused.status_code == 409
    assert refused.json()["code"] == "order.not_repeating"


async def test_nothing_goes_out_before_its_day(
    client: AsyncClient, sessionmaker: Sessions, settings: Settings
) -> None:
    alex = await person(client, ALEX)
    await publish(client, alex, repeat_day=5)
    # The first order stands for this month; next month's copy waits for the 5th.
    assert await run(sessionmaker, settings, datetime.now(UTC)) == 0
    assert await run(sessionmaker, settings, next_month(4)) == 0


# --- allowed ---------------------------------------------------------------------------


async def test_a_copy_goes_out_on_day_n_once_and_is_told_like_a_new_order(
    client: AsyncClient, sessionmaker: Sessions, settings: Settings
) -> None:
    alex = await person(client, ALEX)
    await person(client, NINO)
    await linked(client, sessionmaker, alex, NINO)
    order = await publish(
        client,
        alex,
        repeat_day=5,
        note="как обычно",
        available_until=str(datetime.now(UTC).date() + timedelta(days=10)),
    )
    assert order["repeat_day"] == 5
    assert await run(sessionmaker, settings, next_month(5)) == 1
    # Run again, or late in the month: still the one copy (ADR-0005).
    assert await run(sessionmaker, settings, next_month(5)) == 0
    assert await run(sessionmaker, settings, next_month(20)) == 0

    first, copy = await series(sessionmaker, order)
    assert copy.number > first.number
    assert copy.status == "open"
    assert copy.available_from == next_month(5).date()
    # The same window, from the copy's own day.
    assert copy.available_until == next_month(5).date() + timedelta(days=10)
    assert (copy.amount_max, copy.note, copy.reach, copy.repeat_day) == (
        first.amount_max,
        "как обычно",
        first.reach,
        5,
    )
    assert copy.series_month == next_month(1).date()
    async with sessionmaker() as db:
        told = list(
            await db.scalars(select(Notification.target).where(Notification.type == "order.opened"))
        )
    assert told == [f"order_{first.id}", f"order_{copy.id}"]


async def test_a_fixed_rate_stays_fixed_and_the_market_follows_the_market(
    client: AsyncClient, sessionmaker: Sessions, settings: Settings
) -> None:
    alex = await person(client, ALEX)
    order = await publish(
        client,
        alex,
        repeat_day=1,
        wants=[want("GEL", "GE", fixed("GEL", "RUB", "29.20")), want("USD", "GE")],
    )
    await run(sessionmaker, settings, next_month(1))
    _, copy = await series(sessionmaker, order)
    assert [w.rate_spec for w in copy.wants] == [fixed("GEL", "RUB", "29.20"), MARKET]


async def test_stopping_on_any_order_of_the_series_ends_it(
    client: AsyncClient, sessionmaker: Sessions, settings: Settings
) -> None:
    alex = await person(client, ALEX)
    order = await publish(client, alex, repeat_day=3)
    await run(sessionmaker, settings, next_month(3))
    _, copy = await series(sessionmaker, order)
    stopped = await client.post(f"/api/v1/orders/{copy.id}/stop-repeating", headers=alex)
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["repeat_day"] is None
    first = (await client.get(f"/api/v1/orders/{order['id']}", headers=alex)).json()
    assert first["repeat_day"] is None
    later = next_month(3) + timedelta(days=40)
    assert await run(sessionmaker, settings, later) == 0


async def test_a_copy_at_0_goes_only_to_those_still_linked(
    client: AsyncClient, sessionmaker: Sessions, settings: Settings
) -> None:
    alex = await person(client, ALEX)
    nino = await person(client, NINO)
    link_id = await linked(client, sessionmaker, alex, NINO)
    me = (await client.get("/api/v1/me", headers=nino)).json()
    await publish(client, alex, repeat_day=2, reach=0, visible_to=[me["id"]])
    await client.delete(f"/api/v1/links/{link_id}", headers=nino)
    # Nobody on its list is linked any more: nothing goes out this month.
    assert await run(sessionmaker, settings, next_month(2)) == 0


def test_a_short_month_repeats_on_its_last_day() -> None:
    assert due_day(date(2026, 11, 1), 31) == date(2026, 11, 30)
    assert due_day(date(2027, 2, 1), 30) == date(2027, 2, 28)
    assert due_day(date(2028, 2, 1), 31) == date(2028, 2, 29)
    assert due_day(date(2026, 12, 1), 5) == date(2026, 12, 5)
