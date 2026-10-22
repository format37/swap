"""Recurring orders: a copy every month on day N (QUESTIONS K7, ADR-0036).

The latest order of a series is its template. Once the author's own calendar reaches day
N of a month the series has no order for yet (the month's last day, if it is shorter),
the worker publishes a copy: a new number, today's dates, the same amounts, ways, rates
and reach, and the same announcement as any new order. A fixed rate stays fixed, and the
market's follows the market. The first order stands for its own month, so copies start
the month after it.

The sweep is idempotent and survives restarts (ADR-0005). The database allows one order
per series and month, so a second run, or a run racing it, publishes nothing more. A
missed month isn't made up: only the current one is due.
"""

import calendar
from collections.abc import Collection
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from swap import orders
from swap.db import Sessionmaker
from swap.links import linked_ids
from swap.models import Order, OrderVisibility, User
from swap.orders import OrderDraft, Want
from swap.rates import parse_spec

log = structlog.get_logger("swap.repeats")


def due_day(month: date, repeat_day: int) -> date:
    """Day N of `month`, or its last day when the month is shorter."""
    return month.replace(day=min(repeat_day, calendar.monthrange(month.year, month.month)[1]))


async def _templates(db: AsyncSession) -> list[Order]:
    """The latest order of every series still repeating."""
    found = await db.scalars(
        select(Order)
        .where(Order.repeat_day.is_not(None), Order.series_id.is_not(None))
        .order_by(Order.series_id, Order.series_month.desc())
        .ext(distinct_on(Order.series_id))
    )
    return list(found)


async def _copy(
    db: AsyncSession, template: Order, author: User, today: date, assets: Collection[str]
) -> Order | None:
    """This month's copy of `template`, or None when nobody on its list is still linked."""
    visible_to = None
    if template.reach == 0:
        listed = set(
            await db.scalars(
                select(OrderVisibility.user_id).where(OrderVisibility.order_id == template.id)
            )
        )
        visible_to = list(listed & set(await db.scalars(linked_ids(author.id))))
        if not visible_to:
            return None
    window = (
        template.available_until - template.available_from if template.available_until else None
    )
    draft = OrderDraft(
        give_currency=template.give_currency,
        give_country=template.give_country,
        amount_min=template.amount_min,
        amount_max=template.amount_max,
        available_from=today,
        available_until=today + window if window is not None else None,
        payout_methods=template.payout_methods,
        receive_methods=template.receive_methods,
        wants=[
            Want(currency=w.currency, country=w.country, rate_spec=parse_spec(w.rate_spec))
            for w in template.wants
        ],
        reach=template.reach,
        repeat_day=template.repeat_day,
        visible_to=visible_to,
        note=template.note,
    )
    series = (template.series_id or template.id, today.replace(day=1))
    return await orders.create(db, author, draft, assets, series=series)


async def repeat_due(db: AsyncSession, assets: Collection[str], now: datetime) -> int:
    """Publish every copy due at `now`; returns how many went out."""
    published = 0
    for template in await _templates(db):
        author = await db.get(User, template.author_id)
        if author is None or author.deleted_at is not None or template.repeat_day is None:
            continue
        today = now.astimezone(ZoneInfo(author.tz or "UTC")).date()
        month = today.replace(day=1)
        if template.series_month is not None and template.series_month >= month:
            continue
        if today < due_day(month, template.repeat_day):
            continue
        try:
            async with db.begin_nested():
                copy = await _copy(db, template, author, today, assets)
        except IntegrityError:
            # Another run published this month's copy first.
            continue
        if copy is None:
            log.info("repeat skipped: nobody on its list is linked", series=str(template.series_id))
            continue
        published += 1
    return published


async def repeat_orders(sessionmaker: Sessionmaker, assets: Collection[str]) -> int:
    """The worker's sweep: every copy due now, in one transaction."""
    async with sessionmaker() as db:
        published = await repeat_due(db, assets, datetime.now(UTC))
        await db.commit()
    return published
