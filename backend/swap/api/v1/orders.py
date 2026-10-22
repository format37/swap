"""Orders (ADR-0016): the wizard publishes one, the feeds list them, the card shows one."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel
from sqlalchemy import select

from swap import orders
from swap.api.deps import AppSettings, CurrentUser, Db
from swap.api.errors import Problem
from swap.api.v1.people import Person
from swap.models import Order as OrderRow
from swap.models import OrderStatus, PaymentKind, User
from swap.network import Graph
from swap.orders import OrderDraft, Want
from swap.rates import parse_spec

router = APIRouter(prefix="/orders", tags=["orders"], responses={401: {"model": Problem}})


class Visibility(BaseModel):
    """Who may see an order. Its author alone is told."""

    # Handshakes (ADR-0028): 0 for its list alone, 1 to 3, None for any chain at all.
    reach: int | None
    # At reach 0, the people on its list.
    people: list[Person]


class Order(BaseModel):
    id: uuid.UUID
    # «№ 17» (QUESTIONS K8).
    number: int
    author: Person
    # Whether the signed-in user wrote it.
    mine: bool
    give_currency: str
    give_country: str
    amount_min: Decimal
    amount_max: Decimal
    amount_remaining: Decimal
    available_from: date
    # None: open until its author closes it.
    available_until: date | None
    payout_methods: list[PaymentKind]
    receive_methods: list[PaymentKind]
    # Each with its own rate (ADR-0026).
    wants: list[Want]
    note: str | None
    status: OrderStatus
    # «Повторять каждый месяц, N-го числа», None once it doesn't (QUESTIONS K7).
    repeat_day: int | None
    created_at: datetime
    # Only for its author.
    visibility: Visibility | None = None
    # On someone else's card: the people between them and its author on one shortest chain
    # of links, [] for a direct link (QUESTIONS J2). None in lists, on the author's own,
    # and once no chain joins them.
    chain: list[Person] | None = None

    @classmethod
    def of(cls, order: OrderRow, author: User, viewer: uuid.UUID) -> Self:
        return cls(
            id=order.id,
            number=order.number,
            author=Person.of(author),
            mine=order.author_id == viewer,
            give_currency=order.give_currency,
            give_country=order.give_country,
            amount_min=order.amount_min,
            amount_max=order.amount_max,
            amount_remaining=order.amount_remaining,
            available_from=order.available_from,
            available_until=order.available_until,
            payout_methods=[PaymentKind(kind) for kind in order.payout_methods],
            receive_methods=[PaymentKind(kind) for kind in order.receive_methods],
            wants=[
                Want(
                    currency=want.currency,
                    country=want.country,
                    rate_spec=parse_spec(want.rate_spec),
                )
                for want in order.wants
            ],
            note=order.note,
            status=OrderStatus(order.status),
            repeat_day=order.repeat_day,
            created_at=order.created_at,
        )


async def _with_visibility(db: Db, order: OrderRow, author: User, viewer: uuid.UUID) -> Order:
    shown = Order.of(order, author, viewer)
    if shown.mine:
        people = await orders.chosen_viewers(db, order.id)
        shown.visibility = Visibility(
            reach=order.reach, people=[Person.of(person) for person in people or []]
        )
    else:
        between = (await Graph.load(db)).chain(viewer, author.id)
        if between is not None:
            found = {
                user.id: user for user in await db.scalars(select(User).where(User.id.in_(between)))
            }
            shown.chain = [Person.of(found[person]) for person in between]
    return shown


@router.post("", status_code=201, responses={422: {"model": Problem}})
async def create_order(body: OrderDraft, user: CurrentUser, db: Db, settings: AppSettings) -> Order:
    order = await orders.create(db, user, body, settings.assets)
    await db.commit()
    return await _with_visibility(db, order, user, user.id)


@router.get("")
async def list_orders(
    user: CurrentUser,
    db: Db,
    scope: Literal["visible", "mine", "history"] = "visible",
    within: Annotated[int | None, Query(ge=1, le=3)] = None,
) -> list[Order]:
    """«Открытые мне» (`visible`), «Мои» (`mine`, the open ones) or the finished ones that
    are mine or that I had a deal on (`history`). `within` narrows «Открытые мне» to
    authors at most so many handshakes away (QUESTIONS J2)."""
    found = await orders.feed(db, user.id, scope, within)
    return [Order.of(order, author, user.id) for order, author in found]


@router.get("/{order_id}", responses={404: {"model": Problem}})
async def get_order(order_id: uuid.UUID, user: CurrentUser, db: Db) -> Order:
    order, author = await orders.get(db, user.id, order_id)
    return await _with_visibility(db, order, author, user.id)


@router.post("/{order_id}/close", responses={404: {"model": Problem}, 409: {"model": Problem}})
async def close_order(order_id: uuid.UUID, user: CurrentUser, db: Db) -> Order:
    order = await orders.close(db, user.id, order_id)
    await db.commit()
    return await _with_visibility(db, order, user, user.id)


@router.post("/{order_id}/reopen", responses={404: {"model": Problem}, 409: {"model": Problem}})
async def reopen_order(order_id: uuid.UUID, user: CurrentUser, db: Db) -> Order:
    """A closed order, open again as it was (QUESTIONS F7)."""
    order = await orders.reopen(db, user, order_id)
    await db.commit()
    return await _with_visibility(db, order, user, user.id)


@router.post(
    "/{order_id}/stop-repeating", responses={404: {"model": Problem}, 409: {"model": Problem}}
)
async def stop_repeating(order_id: uuid.UUID, user: CurrentUser, db: Db) -> Order:
    """«Больше не повторять»: no more monthly copies of this series (QUESTIONS K7)."""
    order = await orders.stop_repeating(db, user.id, order_id)
    await db.commit()
    return await _with_visibility(db, order, user, user.id)


@router.delete(
    "/{order_id}", status_code=204, responses={404: {"model": Problem}, 409: {"model": Problem}}
)
async def delete_order(order_id: uuid.UUID, user: CurrentUser, db: Db) -> Response:
    """Delete a finished order with all its deals, for yourself alone (QUESTIONS J3). Whoever
    dealt on it keeps their deals and the order with them."""
    await orders.delete(db, user.id, order_id)
    await db.commit()
    return Response(status_code=204)
