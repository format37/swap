"""Deals (ADR-0018): proposed from an order, moved only by the state machine in swap/deals.py."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from fastapi import APIRouter, Path, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from swap import deals
from swap.api.deps import CurrentUser, Db
from swap.api.errors import Problem
from swap.api.v1.people import Person
from swap.crypto import Keys, deal_leg_aad
from swap.deals import Dispute, Proposal, Receipt
from swap.models import Deal as DealRow
from swap.models import DealLeg, DealStatus, Event, PaymentKind, User
from swap.rates import FixedRate

router = APIRouter(tags=["deals"], responses={401: {"model": Problem}})

REFUSALS: dict[int | str, dict[str, Any]] = {
    403: {"model": Problem},
    404: {"model": Problem},
    409: {"model": Problem},
}
Seq = Annotated[int, Path(ge=1, le=2)]


class Recipient(BaseModel):
    """Where the payer sends: the payee's chosen payment details (ADR-0010)."""

    title: str | None
    # Null when there is no text, as for cash.
    masked: str | None
    # Only for the payee, and for the payer once the deal was accepted (Q-B8).
    full: str | None


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
    # Null until the payee has chosen: the author chooses when accepting.
    recipient: Recipient | None


class Rate(BaseModel):
    """«1 base = value quote», as the order's author typed it, locked at the proposal."""

    base: str
    quote: str
    value: Decimal


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
    legs: list[Leg]
    events: list[DealEvent]

    @classmethod
    def of(
        cls,
        deal: DealRow,
        people: dict[uuid.UUID, User],
        journal: list[Event],
        viewer: uuid.UUID,
        keys: Keys | None,
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
                    recipient=_recipient(deal, leg, viewer, keys),
                )
                for leg in deal.legs
            ],
            events=[_event(event) for event in journal],
        )


def _recipient(
    deal: DealRow, leg: DealLeg, viewer: uuid.UUID, keys: Keys | None
) -> Recipient | None:
    if leg.recipient_title is None and leg.recipient_details is None:
        return None
    # The payee always reads their own; the payer once the deal was accepted (Q-B8).
    allowed = viewer == leg.payee_id or (viewer == leg.payer_id and deal.accepted_at is not None)
    full = None
    if allowed and leg.recipient_details is not None and keys is not None:
        full = keys.unseal(leg.recipient_details, deal_leg_aad(leg.id)).get_secret_value()
    masked = str(leg.recipient_details["mask"]) if leg.recipient_details else None
    return Recipient(title=leg.recipient_title, masked=masked, full=full)


def _rate(deal: DealRow) -> Rate:
    """The quote as its author typed it («29,20»), from the deal's own copy of the spec."""
    quote = FixedRate.model_validate(deal.rate_spec).quote_for(deal.rate_base, deal.rate_quote)
    return Rate(base=quote.base, quote=quote.quote, value=quote.value)


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


def _keys(request: Request) -> Keys | None:
    keys: Keys | None = request.app.state.keys
    return keys


async def _shown(db: Db, rows: list[DealRow], viewer: uuid.UUID, keys: Keys | None) -> list[Deal]:
    ids = {user for row in rows for user in (row.proposer_id, row.acceptor_id)}
    people = {user.id: user for user in await db.scalars(select(User).where(User.id.in_(ids)))}
    return [Deal.of(row, people, await deals.journal(db, row), viewer, keys) for row in rows]


async def _done(db: Db, row: DealRow, viewer: uuid.UUID, request: Request) -> Deal:
    await db.commit()
    # Read back what was stored, so a response looks like any later read of the same deal.
    fresh = await db.scalar(
        select(DealRow).where(DealRow.id == row.id).execution_options(populate_existing=True)
    )
    [shown] = await _shown(db, [fresh or row], viewer, _keys(request))
    return shown


@router.post(
    "/orders/{order_id}/deals",
    status_code=201,
    responses={**REFUSALS, 422: {"model": Problem}, 503: {"model": Problem}},
)
async def propose_deal(
    order_id: uuid.UUID, body: Proposal, request: Request, user: CurrentUser, db: Db
) -> Deal:
    """Propose a deal on an order open to you (FR-4.1)."""
    row = await deals.propose(db, user, order_id, body, _keys(request))
    return await _done(db, row, user.id, request)


@router.get("/deals")
async def list_deals(
    request: Request,
    user: CurrentUser,
    db: Db,
    scope: Literal["active", "history"] = "active",
    order_id: uuid.UUID | None = None,
) -> list[Deal]:
    """Your deals: open ones, or closed ones; on one order, if you name it."""
    rows = await deals.mine(db, user.id, scope, order_id)
    return await _shown(db, rows, user.id, _keys(request))


@router.get("/deals/{deal_id}", responses={404: {"model": Problem}})
async def get_deal(deal_id: uuid.UUID, request: Request, user: CurrentUser, db: Db) -> Deal:
    row = await deals.get(db, user.id, deal_id)
    [shown] = await _shown(db, [row], user.id, _keys(request))
    return shown


@router.post(
    "/deals/{deal_id}/accept",
    responses={**REFUSALS, 422: {"model": Problem}, 503: {"model": Problem}},
)
async def accept_deal(
    deal_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    db: Db,
    body: Receipt | None = None,
) -> Deal:
    """Accept a proposal on your order. Cash needs no payment details, so no body either."""
    row = await deals.accept(db, user, deal_id, body or Receipt(), _keys(request))
    return await _done(db, row, user.id, request)


@router.post("/deals/{deal_id}/decline", responses=REFUSALS)
async def decline_deal(deal_id: uuid.UUID, request: Request, user: CurrentUser, db: Db) -> Deal:
    return await _done(db, await deals.decline(db, user, deal_id), user.id, request)


@router.post("/deals/{deal_id}/withdraw", responses=REFUSALS)
async def withdraw_deal(deal_id: uuid.UUID, request: Request, user: CurrentUser, db: Db) -> Deal:
    return await _done(db, await deals.withdraw(db, user, deal_id), user.id, request)


@router.post("/deals/{deal_id}/cancel", responses=REFUSALS)
async def cancel_deal(deal_id: uuid.UUID, request: Request, user: CurrentUser, db: Db) -> Deal:
    """Before the first «Отправлено», either side cancels alone (FR-4.5)."""
    return await _done(db, await deals.cancel(db, user, deal_id), user.id, request)


@router.post("/deals/{deal_id}/legs/{seq}/sent", responses=REFUSALS)
async def mark_sent(
    deal_id: uuid.UUID, seq: Seq, request: Request, user: CurrentUser, db: Db
) -> Deal:
    return await _done(db, await deals.mark_sent(db, user, deal_id, seq), user.id, request)


@router.post("/deals/{deal_id}/legs/{seq}/received", responses=REFUSALS)
async def mark_received(
    deal_id: uuid.UUID, seq: Seq, request: Request, user: CurrentUser, db: Db
) -> Deal:
    return await _done(db, await deals.mark_received(db, user, deal_id, seq), user.id, request)


@router.post("/deals/{deal_id}/cancel-request", responses=REFUSALS)
async def request_cancel(deal_id: uuid.UUID, request: Request, user: CurrentUser, db: Db) -> Deal:
    """After the first «Отправлено», ask the other side to cancel (FR-4.5)."""
    return await _done(db, await deals.request_cancel(db, user, deal_id), user.id, request)


@router.post("/deals/{deal_id}/cancel-request/approve", responses=REFUSALS)
async def approve_cancel(deal_id: uuid.UUID, request: Request, user: CurrentUser, db: Db) -> Deal:
    row = await deals.answer_cancel(db, user, deal_id, approve=True)
    return await _done(db, row, user.id, request)


@router.post("/deals/{deal_id}/cancel-request/reject", responses=REFUSALS)
async def reject_cancel(deal_id: uuid.UUID, request: Request, user: CurrentUser, db: Db) -> Deal:
    row = await deals.answer_cancel(db, user, deal_id, approve=False)
    return await _done(db, row, user.id, request)


@router.post("/deals/{deal_id}/dispute", responses={**REFUSALS, 422: {"model": Problem}})
async def dispute_deal(
    deal_id: uuid.UUID, body: Dispute, request: Request, user: CurrentUser, db: Db
) -> Deal:
    """«Проблема», with a word on what went wrong (FR-4.6)."""
    return await _done(db, await deals.dispute(db, user, deal_id, body.note), user.id, request)


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["settled", "cancelled"]


@router.post("/deals/{deal_id}/resolve", responses={**REFUSALS, 422: {"model": Problem}})
async def resolve_deal(
    deal_id: uuid.UUID, body: Resolution, request: Request, user: CurrentUser, db: Db
) -> Deal:
    """Propose how a dispute ended; the same outcome from the other side settles it."""
    row = await deals.resolve(db, user, deal_id, body.outcome)
    return await _done(db, row, user.id, request)
