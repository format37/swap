"""Orders: intents to give one currency and take another, seen only through links (ADR-0016).

Who sees an order is one predicate, `seen_by`, used by every query here: nobody once it
is deleted; the author always until then; anyone else only while it is open and its last
day, if it has one, hasn't passed, through an active link with the author, and when they
are on its list, if it has one (§3).
"""

import uuid
from collections.abc import Collection
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ColumnElement, Date, and_, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from swap.deeplinks import target
from swap.errors import DomainError
from swap.links import linked_ids
from swap.models import Order, OrderStatus, OrderVisibility, OrderWant, PaymentKind, User
from swap.money import Asset, Country, Money, MoneyOrZero
from swap.notifications import notify
from swap.proposals import cancel_on_order
from swap.rates import CENT, FixedRate
from swap.users import person_label


class Want(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: Asset
    country: Country


class OrderDraft(BaseModel):
    """What the wizard publishes (FR-2.1). A value from a form, checked here for its rules."""

    model_config = ConfigDict(extra="forbid")

    give_currency: Asset
    give_country: Country
    # The smallest single deal: 0 for any amount (QUESTIONS F4), amount_max for «exactly
    # this much» (Q-B5).
    amount_min: MoneyOrZero
    amount_max: Money
    available_from: date
    # None: open until its author closes it (QUESTIONS F3).
    available_until: date | None = None
    payout_methods: list[PaymentKind] = Field(min_length=1, max_length=len(PaymentKind))
    # How the author can be paid, whichever currency they get (QUESTIONS F2).
    receive_methods: list[PaymentKind] = Field(min_length=1, max_length=len(PaymentKind))
    wants: list[Want] = Field(min_length=1, max_length=8)
    rate_spec: FixedRate
    # None: all active links, now and later. Otherwise only these, who must be links now.
    visible_to: list[uuid.UUID] | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=500)


def today(user: User) -> date:
    """The date in the user's time zone, which order dates are in (Q-B17)."""
    return datetime.now(ZoneInfo(user.tz or "UTC")).date()


def smallest_deal(order: Order) -> Decimal:
    """The least one deal may take: the order's minimum, and a cent when that is 0 (F4)."""
    return max(order.amount_min, CENT)


def _authors_today() -> ColumnElement[date]:
    # An alias, so the subquery keeps its own FROM where the author is joined already.
    author = aliased(User)
    tz = select(func.coalesce(author.tz, "UTC")).where(author.id == Order.author_id)
    return cast(func.timezone(tz.scalar_subquery(), func.now()), Date)


def seen_by(viewer: uuid.UUID) -> ColumnElement[bool]:
    """Whether `viewer` may see an order: the trust boundary of §3, in one place."""
    unlisted = ~exists().where(OrderVisibility.order_id == Order.id)
    listed = exists().where(OrderVisibility.order_id == Order.id, OrderVisibility.user_id == viewer)
    return and_(
        # A deleted order is nobody's, its author's included (QUESTIONS F6).
        Order.deleted_at.is_(None),
        or_(
            Order.author_id == viewer,
            and_(
                Order.status == OrderStatus.OPEN,
                # Until the expiry sweep (slice 5) marks it, an order past its dates is over.
                or_(Order.available_until.is_(None), Order.available_until >= _authors_today()),
                Order.author_id.in_(linked_ids(viewer)),
                or_(unlisted, listed),
            ),
        ),
    )


def _check(draft: OrderDraft, author: User, assets: Collection[str]) -> None:
    wanted = [want.currency for want in draft.wants]
    if any(currency not in assets for currency in [draft.give_currency, *wanted]):
        raise DomainError(422, "order.unknown_currency")
    if draft.give_currency in wanted:
        raise DomainError(422, "order.wants_own_currency")
    if len({(want.currency, want.country) for want in draft.wants}) != len(draft.wants):
        raise DomainError(422, "order.wants_repeated")
    # One rate for each wanted currency, and none for anything else (ADR-0004).
    for currency in set(wanted):
        draft.rate_spec.quote_for(draft.give_currency, currency)
    pairs = {frozenset((draft.give_currency, currency)) for currency in wanted}
    quoted = [frozenset((quote.base, quote.quote)) for quote in draft.rate_spec.quotes]
    if len(quoted) != len(set(quoted)) or not set(quoted) <= pairs:
        raise DomainError(422, "rate.unused")
    if draft.amount_min > draft.amount_max:
        raise DomainError(422, "order.amount_range")
    if draft.available_until is not None:
        if draft.available_from > draft.available_until:
            raise DomainError(422, "order.window")
        if draft.available_until < today(author):
            raise DomainError(422, "order.window_past")


async def create(
    db: AsyncSession, author: User, draft: OrderDraft, assets: Collection[str]
) -> Order:
    """Publish an order and tell everyone who can see it (FR-2.1, FR-7.1)."""
    _check(draft, author, assets)
    links = set(await db.scalars(linked_ids(author.id)))
    if draft.visible_to is not None:
        chosen = set(draft.visible_to)
        if not chosen:
            raise DomainError(422, "order.visible_to_nobody")
        if not chosen <= links:
            raise DomainError(422, "order.visible_to_unlinked")
    # In cents, as numeric(18,2) keeps them: "0" reads back as "0.00".
    least, most = draft.amount_min.quantize(CENT), draft.amount_max.quantize(CENT)
    order = Order(
        id=uuid.uuid4(),
        author_id=author.id,
        give_currency=draft.give_currency,
        give_country=draft.give_country,
        amount_min=least,
        amount_max=most,
        amount_remaining=most,
        available_from=draft.available_from,
        available_until=draft.available_until,
        payout_methods=list(dict.fromkeys(draft.payout_methods)),
        receive_methods=list(dict.fromkeys(draft.receive_methods)),
        note=(draft.note or "").strip() or None,
        rate_spec=draft.rate_spec.model_dump(mode="json"),
        status=OrderStatus.OPEN,
        wants=[
            OrderWant(currency=want.currency, country=want.country, position=position)
            for position, want in enumerate(draft.wants)
        ],
    )
    db.add(order)
    audience = links if draft.visible_to is None else set(draft.visible_to)
    for viewer in audience:
        if draft.visible_to is not None:
            db.add(OrderVisibility(order_id=order.id, user_id=viewer))
        notify(
            db,
            viewer,
            "order.opened",
            target=target("order", order.id),
            name=person_label(author),
            amount=str(order.amount_max),
            currency=order.give_currency,
            wants=", ".join(dict.fromkeys(want.currency for want in draft.wants)),
        )
    await db.flush()
    return order


async def feed(
    db: AsyncSession, viewer: uuid.UUID, scope: Literal["visible", "mine"]
) -> list[tuple[Order, User]]:
    """«Открытые мне», earliest available first (FR-2.4); or «Мои», open ones first."""
    query = select(Order, User).join(User, User.id == Order.author_id)
    if scope == "mine":
        query = query.where(Order.author_id == viewer, seen_by(viewer)).order_by(
            (Order.status != OrderStatus.OPEN), Order.created_at.desc()
        )
    else:
        query = query.where(Order.author_id != viewer, seen_by(viewer)).order_by(
            Order.available_from, Order.created_at
        )
    return [(order, author) for order, author in await db.execute(query)]


async def get(db: AsyncSession, viewer: uuid.UUID, order_id: uuid.UUID) -> tuple[Order, User]:
    row = (
        await db.execute(
            select(Order, User)
            .join(User, User.id == Order.author_id)
            .where(Order.id == order_id, seen_by(viewer))
        )
    ).first()
    if row is None:
        # The same answer whether it doesn't exist or isn't for this viewer.
        raise DomainError(404, "order.not_found")
    order, author = row
    return order, author


async def chosen_viewers(db: AsyncSession, order_id: uuid.UUID) -> list[User] | None:
    """Who an order is limited to; None when it is for all links. For its author only."""
    people = list(
        await db.scalars(
            select(User)
            .join(OrderVisibility, OrderVisibility.user_id == User.id)
            .where(OrderVisibility.order_id == order_id)
            .order_by(User.first_name)
        )
    )
    return people or None


async def _own(db: AsyncSession, author: uuid.UUID, order_id: uuid.UUID) -> Order:
    """The author's own order, locked; 404 for anyone else's, or for one deleted."""
    order = await db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.author_id == author, Order.deleted_at.is_(None))
        .with_for_update()
    )
    if order is None:
        raise DomainError(404, "order.not_found")
    return order


async def close(db: AsyncSession, author: uuid.UUID, order_id: uuid.UUID) -> Order:
    """The author closes what remains (FR-2.5). Accepted deals carry on."""
    order = await _own(db, author, order_id)
    if order.status != OrderStatus.OPEN:
        raise DomainError(409, "order.not_open")
    order.status = OrderStatus.CLOSED
    # Its unanswered proposals have nothing left to take (Q-E2).
    await cancel_on_order(db, order, author)
    return order


async def reopen(db: AsyncSession, author: User, order_id: uuid.UUID) -> Order:
    """A closed order opens again as it was: its remainder, list and dates (QUESTIONS F7).

    Nobody is told again, and the proposals cancelled at closing stay cancelled.
    """
    order = await _own(db, author.id, order_id)
    if order.status != OrderStatus.CLOSED:
        raise DomainError(409, "order.not_closed")
    if order.available_until is not None and order.available_until < today(author):
        raise DomainError(409, "order.window_past")
    order.status = OrderStatus.OPEN
    return order


async def delete(db: AsyncSession, author: uuid.UUID, order_id: uuid.UUID) -> None:
    """The author deletes an order that isn't open (QUESTIONS F6). Its deals carry on.

    An open one is closed first, which cancels its proposals (Q-E2).
    """
    order = await _own(db, author, order_id)
    if order.status == OrderStatus.OPEN:
        raise DomainError(409, "order.open")
    order.deleted_at = datetime.now(UTC)
