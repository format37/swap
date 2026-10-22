"""Orders (ADR-0016): the wizard publishes one, the feeds list them, the card shows one."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from fastapi import APIRouter, Response
from pydantic import BaseModel

from swap import orders
from swap.api.deps import AppSettings, CurrentUser, Db
from swap.api.errors import Problem
from swap.api.v1.people import Person
from swap.models import Order as OrderRow
from swap.models import OrderStatus, PaymentKind, User
from swap.orders import OrderDraft, Want
from swap.rates import parse_spec

router = APIRouter(prefix="/orders", tags=["orders"], responses={401: {"model": Problem}})


class Visibility(BaseModel):
    """Who may see an order. Its author alone is told."""

    all_links: bool
    people: list[Person]


class Order(BaseModel):
    id: uuid.UUID
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
    created_at: datetime
    # Only for its author.
    visibility: Visibility | None = None

    @classmethod
    def of(cls, order: OrderRow, author: User, viewer: uuid.UUID) -> Self:
        return cls(
            id=order.id,
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
            created_at=order.created_at,
        )


async def _with_visibility(db: Db, order: OrderRow, author: User, viewer: uuid.UUID) -> Order:
    shown = Order.of(order, author, viewer)
    if shown.mine:
        people = await orders.chosen_viewers(db, order.id)
        shown.visibility = Visibility(
            all_links=people is None, people=[Person.of(person) for person in people or []]
        )
    return shown


@router.post("", status_code=201, responses={422: {"model": Problem}})
async def create_order(body: OrderDraft, user: CurrentUser, db: Db, settings: AppSettings) -> Order:
    order = await orders.create(db, user, body, settings.assets)
    await db.commit()
    return await _with_visibility(db, order, user, user.id)


@router.get("")
async def list_orders(
    user: CurrentUser, db: Db, scope: Literal["visible", "mine", "history"] = "visible"
) -> list[Order]:
    """«Открытые мне» (`visible`), «Мои» (`mine`, the open ones) or the finished ones that
    are mine or that I had a deal on (`history`)."""
    found = await orders.feed(db, user.id, scope)
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


@router.delete(
    "/{order_id}", status_code=204, responses={404: {"model": Problem}, 409: {"model": Problem}}
)
async def delete_order(order_id: uuid.UUID, user: CurrentUser, db: Db) -> Response:
    """Gone for everyone, its author included; its deals carry on (QUESTIONS F6)."""
    await orders.delete(db, user.id, order_id)
    await db.commit()
    return Response(status_code=204)
