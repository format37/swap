"""Deals (ADR-0018): proposed from an order, moved only by the state machine in swap/deals.py."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from fastapi import APIRouter, Path
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from swap import deals
from swap.api.deps import CurrentUser, Db, MarketRates
from swap.api.errors import Problem
from swap.api.v1.people import Person
from swap.deals import Dispute, Proposal
from swap.models import Deal as DealRow
from swap.models import DealStatus, Event, PaymentKind, User
from swap.rates import FixedRate

router = APIRouter(tags=["deals"], responses={401: {"model": Problem}})

REFUSALS: dict[int | str, dict[str, Any]] = {
    403: {"model": Problem},
    404: {"model": Problem},
    409: {"model": Problem},
}
Seq = Annotated[int, Path(ge=1, le=2)]


class Leg(BaseModel):
    seq: int
    payer: Person
    payee: Person
    currency: str
    country: str
    amount: Decimal
    method: PaymentKind
    due_date: date
    sent_at: datetime | None
    received_at: datetime | None


class Rate(BaseModel):
    """«1 base = value quote», as the order's author typed it or the market had it, locked
    at the proposal."""

    base: str
    quote: str
    value: Decimal
    # The market's: its source, and when it said so (FR-3.5). None for the author's own.
    source: Literal["coinbase"] | None = None
    fetched_at: datetime | None = None


class DealEvent(BaseModel):
    """A line of the deal's journal (FR-4.7)."""

    type: str
    # Null for the system, as for an expiry.
    actor_id: uuid.UUID | None
    at: datetime
    to: DealStatus
    seq: int | None = None
    note: str | None = None
    outcome: str | None = None
    reason: str | None = None


class Deal(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: DealStatus
    # Which side the signed-in user is on.
    role: Literal["proposer", "acceptor"]
    proposer: Person
    acceptor: Person
    rate: Rate
    whole: bool
    expires_at: datetime
    accepted_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    cancel_requested_by: uuid.UUID | None
    disputed_by: uuid.UUID | None
    dispute_note: str | None
    resolution: str | None
    resolution_by: uuid.UUID | None
    # The proposer's word on the rest, such as which bank (QUESTIONS G3).
    note: str | None
    legs: list[Leg]
    events: list[DealEvent]

    @classmethod
    def of(
        cls,
        deal: DealRow,
        people: dict[uuid.UUID, User],
        journal: list[Event],
        viewer: uuid.UUID,
    ) -> Self:
        def person(user_id: uuid.UUID) -> Person:
            return Person.of(people[user_id])

        return cls(
            id=deal.id,
            order_id=deal.order_id,
            status=DealStatus(deal.status),
            role="proposer" if viewer == deal.proposer_id else "acceptor",
            proposer=person(deal.proposer_id),
            acceptor=person(deal.acceptor_id),
            rate=_rate(deal),
            whole=deal.whole,
            expires_at=deal.expires_at,
            accepted_at=deal.accepted_at,
            closed_at=deal.closed_at,
            created_at=deal.created_at,
            cancel_requested_by=deal.cancel_requested_by,
            disputed_by=deal.disputed_by,
            dispute_note=deal.dispute_note,
            resolution=deal.resolution,
            resolution_by=deal.resolution_by,
            note=deal.note,
            legs=[
                Leg(
                    seq=leg.seq,
                    payer=person(leg.payer_id),
                    payee=person(leg.payee_id),
                    currency=leg.currency,
                    country=leg.country,
                    amount=leg.amount,
                    method=PaymentKind(leg.method),
                    due_date=leg.due_date,
                    sent_at=leg.sent_at,
                    received_at=leg.received_at,
                )
                for leg in deal.legs
            ],
            events=[_event(event) for event in journal],
        )


def _rate(deal: DealRow) -> Rate:
    """The quote as it was locked («29,20»), from the deal's own copy of the spec."""
    quote = FixedRate.model_validate(deal.rate_spec).quote_for(deal.rate_base, deal.rate_quote)
    return Rate(
        base=quote.base,
        quote=quote.quote,
        value=quote.value,
        source="coinbase" if deal.rate_source == "coinbase" else None,
        fetched_at=deal.rate_fetched_at,
    )


def _event(event: Event) -> DealEvent:
    payload = event.payload
    return DealEvent(
        type=event.type,
        actor_id=event.actor_id,
        at=event.created_at,
        to=DealStatus(payload["to"]),
        seq=payload.get("seq"),
        note=payload.get("note"),
        outcome=payload.get("outcome"),
        reason=payload.get("reason"),
    )


async def _shown(db: Db, rows: list[DealRow], viewer: uuid.UUID) -> list[Deal]:
    ids = {user for row in rows for user in (row.proposer_id, row.acceptor_id)}
    people = {user.id: user for user in await db.scalars(select(User).where(User.id.in_(ids)))}
    return [Deal.of(row, people, await deals.journal(db, row), viewer) for row in rows]


async def _done(db: Db, row: DealRow, viewer: uuid.UUID) -> Deal:
    await db.commit()
    # Read back what was stored, so a response looks like any later read of the same deal.
    fresh = await db.scalar(
        select(DealRow).where(DealRow.id == row.id).execution_options(populate_existing=True)
    )
    [shown] = await _shown(db, [fresh or row], viewer)
    return shown


@router.post(
    "/orders/{order_id}/deals",
    status_code=201,
    responses={**REFUSALS, 422: {"model": Problem}},
)
async def propose_deal(
    order_id: uuid.UUID, body: Proposal, user: CurrentUser, db: Db, market: MarketRates
) -> Deal:
    """Propose a deal on an order open to you (FR-4.1), at its rate of this moment."""
    row = await deals.propose(db, user, order_id, body, market)
    return await _done(db, row, user.id)


@router.get("/deals")
async def list_deals(
    user: CurrentUser,
    db: Db,
    scope: Literal["active", "history"] = "active",
    order_id: uuid.UUID | None = None,
) -> list[Deal]:
    """Your deals: open ones, or closed ones; on one order, if you name it."""
    rows = await deals.mine(db, user.id, scope, order_id)
    return await _shown(db, rows, user.id)


@router.get("/deals/{deal_id}", responses={404: {"model": Problem}})
async def get_deal(deal_id: uuid.UUID, user: CurrentUser, db: Db) -> Deal:
    row = await deals.get(db, user.id, deal_id)
    [shown] = await _shown(db, [row], user.id)
    return shown


@router.post("/deals/{deal_id}/accept", responses=REFUSALS)
async def accept_deal(deal_id: uuid.UUID, user: CurrentUser, db: Db) -> Deal:
    """Accept a proposal on your order: one tap, no payment details (QUESTIONS G1)."""
    return await _done(db, await deals.accept(db, user, deal_id), user.id)


@router.post("/deals/{deal_id}/decline", responses=REFUSALS)
async def decline_deal(deal_id: uuid.UUID, user: CurrentUser, db: Db) -> Deal:
    return await _done(db, await deals.decline(db, user, deal_id), user.id)


@router.post("/deals/{deal_id}/withdraw", responses=REFUSALS)
async def withdraw_deal(deal_id: uuid.UUID, user: CurrentUser, db: Db) -> Deal:
    return await _done(db, await deals.withdraw(db, user, deal_id), user.id)


@router.post("/deals/{deal_id}/cancel", responses=REFUSALS)
async def cancel_deal(deal_id: uuid.UUID, user: CurrentUser, db: Db) -> Deal:
    """Before the first «Отправлено», either side cancels alone (FR-4.5)."""
    return await _done(db, await deals.cancel(db, user, deal_id), user.id)


@router.post("/deals/{deal_id}/legs/{seq}/sent", responses=REFUSALS)
async def mark_sent(deal_id: uuid.UUID, seq: Seq, user: CurrentUser, db: Db) -> Deal:
    return await _done(db, await deals.mark_sent(db, user, deal_id, seq), user.id)


@router.post("/deals/{deal_id}/legs/{seq}/received", responses=REFUSALS)
async def mark_received(deal_id: uuid.UUID, seq: Seq, user: CurrentUser, db: Db) -> Deal:
    return await _done(db, await deals.mark_received(db, user, deal_id, seq), user.id)


@router.post("/deals/{deal_id}/cancel-request", responses=REFUSALS)
async def request_cancel(deal_id: uuid.UUID, user: CurrentUser, db: Db) -> Deal:
    """After the first «Отправлено», ask the other side to cancel (FR-4.5)."""
    return await _done(db, await deals.request_cancel(db, user, deal_id), user.id)


@router.post("/deals/{deal_id}/cancel-request/approve", responses=REFUSALS)
async def approve_cancel(deal_id: uuid.UUID, user: CurrentUser, db: Db) -> Deal:
    row = await deals.answer_cancel(db, user, deal_id, approve=True)
    return await _done(db, row, user.id)


@router.post("/deals/{deal_id}/cancel-request/reject", responses=REFUSALS)
async def reject_cancel(deal_id: uuid.UUID, user: CurrentUser, db: Db) -> Deal:
    row = await deals.answer_cancel(db, user, deal_id, approve=False)
    return await _done(db, row, user.id)


@router.post("/deals/{deal_id}/dispute", responses={**REFUSALS, 422: {"model": Problem}})
async def dispute_deal(deal_id: uuid.UUID, body: Dispute, user: CurrentUser, db: Db) -> Deal:
    """«Проблема», with a word on what went wrong (FR-4.6)."""
    return await _done(db, await deals.dispute(db, user, deal_id, body.note), user.id)


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["settled", "cancelled"]


@router.post("/deals/{deal_id}/resolve", responses={**REFUSALS, 422: {"model": Problem}})
async def resolve_deal(deal_id: uuid.UUID, body: Resolution, user: CurrentUser, db: Db) -> Deal:
    """Propose how a dispute ended; the same outcome from the other side settles it."""
    row = await deals.resolve(db, user, deal_id, body.outcome)
    return await _done(db, row, user.id)
