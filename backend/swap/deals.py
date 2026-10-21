"""Deals: the state machine of Q-B1, the only code that changes a deal (ADR-0002, ADR-0018).

Every action locks the deal, checks that the actor may take it from the deal's state,
applies it, and journals it through swap/journal.py in the same transaction. A
stranger to a deal gets 404 for everything, as for a deal that doesn't exist. A wrong
state is 409 `deal.invalid_transition`; the other side's move is 403 `deal.not_your_move`.

    proposed ─accept→ accepted ─sent 1→ leg1_sent ─received 1→ leg1_received
        │                │                                        │
        │ decline,       │ cancel                                 sent 2
        │ withdraw,      ↓                                        ↓
        │ expire     cancelled ←─ cancel request, approved ─── leg2_sent ─received 2→ settled
        ↓                ↑                                        │
     cancelled/      disputed ←───── «Проблема» from any of accepted … leg2_sent
     expired             └── resolved as settled or cancelled, by one side, confirmed by the other
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from swap import orders, payment_methods
from swap.crypto import Keys, deal_leg_aad
from swap.deeplinks import target
from swap.errors import DomainError
from swap.journal import TERMINAL, record, start
from swap.models import (
    Deal,
    DealLeg,
    DealStatus,
    Event,
    Order,
    OrderStatus,
    PaymentKind,
    PaymentMethod,
    User,
)
from swap.money import Asset, Money
from swap.notifications import NotificationType, notify
from swap.proposals import cancel_on_order, give_amount
from swap.rates import FixedRate, convert
from swap.users import person_label

PROPOSAL_TTL = timedelta(hours=48)
# Where «Проблема» may be pressed (FR-4.6), and where a cancel needs the other side (FR-4.5).
ACTIVE = frozenset(
    {DealStatus.ACCEPTED, DealStatus.LEG1_SENT, DealStatus.LEG1_RECEIVED, DealStatus.LEG2_SENT}
)
AFTER_FIRST_SENT = ACTIVE - {DealStatus.ACCEPTED}
OPEN_STATES = ACTIVE | {DealStatus.PROPOSED, DealStatus.DISPUTED}


class Proposal(BaseModel):
    """What the proposal form sends (FR-4.1). Amounts are in the order's own currency."""

    model_config = ConfigDict(extra="forbid")

    amount: Money
    want_currency: Asset
    # Round the counter-amount to whole units, for cash (Q-B4).
    whole: bool = False
    # Who sends first; the proposer by default (Q-B16).
    first: Literal["proposer", "author"] = "proposer"
    # How the author pays out: one of the order's own ways.
    give_method: PaymentKind
    # Where the proposer wants it: their saved details for that currency. None for cash.
    receive_with: uuid.UUID | None = None
    # How the proposer pays the other currency: «в ответ GEL наличными».
    counter_method: PaymentKind
    # The due date of the proposer's own transfer, and of the author's.
    my_due: date
    their_due: date


class Receipt(BaseModel):
    """What accepting sends: where the author wants the other currency. None for cash."""

    model_config = ConfigDict(extra="forbid")

    receive_with: uuid.UUID | None = None


class Dispute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # «Проблема» needs a word on what went wrong (FR-4.6).
    note: str = Field(min_length=1, max_length=1000)

    @field_validator("note")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("say what went wrong")
        return value.strip()


def _refuse(code: str, status: int = 409) -> DomainError:
    return DomainError(status, code)


def _require(deal: Deal, *states: DealStatus) -> None:
    if deal.status not in states:
        raise _refuse("deal.invalid_transition")


def _mine(allowed: bool) -> None:
    if not allowed:
        raise _refuse("deal.not_your_move", 403)


def _other(deal: Deal, me: uuid.UUID) -> uuid.UUID:
    return deal.acceptor_id if me == deal.proposer_id else deal.proposer_id


def _leg(deal: Deal, seq: int) -> DealLeg:
    for leg in deal.legs:
        if leg.seq == seq:
            return leg
    raise _refuse("deal.no_such_leg", 404)


def _tell(
    db: AsyncSession, deal: Deal, to: uuid.UUID, kind: NotificationType, about: User, **values: str
) -> None:
    notify(db, to, kind, target=target("deal", deal.id), name=person_label(about), **values)


async def _lock(db: AsyncSession, me: uuid.UUID, deal_id: uuid.UUID) -> Deal:
    deal = await db.scalar(
        select(Deal)
        .where(Deal.id == deal_id, or_(Deal.proposer_id == me, Deal.acceptor_id == me))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if deal is None:
        raise _refuse("deal.not_found", 404)
    return deal


async def _fill_details(
    db: AsyncSession,
    leg: DealLeg,
    payee: uuid.UUID,
    method_id: uuid.UUID | None,
    keys: Keys | None,
) -> None:
    """Copy the payee's chosen payment details into the leg, sealed for it (ADR-0010)."""
    if method_id is None:
        # Cash needs no details: they meet.
        if leg.method != PaymentKind.CASH:
            raise _refuse("deal.details_required", 422)
        return
    entry = await db.scalar(
        select(PaymentMethod).where(PaymentMethod.id == method_id, PaymentMethod.user_id == payee)
    )
    if entry is None:
        raise _refuse("deal.details_unknown", 422)
    if entry.asset != leg.currency:
        raise _refuse("deal.details_mismatch", 422)
    leg.recipient_title = entry.title
    if entry.details is not None:
        text = payment_methods.reveal(entry, keys)
        if keys is None or text is None:
            raise _refuse("payment.unavailable", 503)
        leg.recipient_details = keys.seal(text, deal_leg_aad(leg.id))


async def _restore(db: AsyncSession, deal: Deal) -> None:
    """An accepted deal that ends cancelled gives its amount back to the order (FR-2.3)."""
    order = await db.scalar(select(Order).where(Order.id == deal.order_id).with_for_update())
    if order is None:  # pragma: no cover - the foreign key guarantees the row
        return
    order.amount_remaining = min(order.amount_max, order.amount_remaining + give_amount(deal))
    if order.status == OrderStatus.FULFILLED and order.amount_remaining >= order.amount_min:
        order.status = OrderStatus.OPEN


async def propose(
    db: AsyncSession, proposer: User, order_id: uuid.UUID, proposal: Proposal, keys: Keys | None
) -> Deal:
    """A deal proposed on an order the proposer can see (FR-4.1)."""
    order, author = await orders.get(db, proposer.id, order_id)
    if author.id == proposer.id:
        raise _refuse("deal.own_order")
    if order.status != OrderStatus.OPEN:
        raise _refuse("order.not_open")
    want = next((w for w in order.wants if w.currency == proposal.want_currency), None)
    if want is None:
        raise _refuse("deal.unknown_want", 422)
    # At least the smallest deal, at most what remains (Q-B5).
    if not order.amount_min <= proposal.amount <= order.amount_remaining:
        raise _refuse("deal.amount_range", 422)
    if proposal.give_method not in order.payout_methods:
        raise _refuse("deal.method_not_offered", 422)
    today = orders.today(proposer)
    if min(proposal.my_due, proposal.their_due) < today:
        raise _refuse("deal.due_past", 422)

    spec = FixedRate.model_validate(order.rate_spec)
    quote = spec.quote_for(order.give_currency, want.currency)
    counter = convert(
        proposal.amount, spec, order.give_currency, want.currency, whole=proposal.whole
    )
    if counter <= 0:
        raise _refuse("deal.amount_range", 422)

    now = datetime.now(UTC)
    deal = Deal(
        id=uuid.uuid4(),
        order_id=order.id,
        proposer_id=proposer.id,
        acceptor_id=author.id,
        status=DealStatus.PROPOSED,
        rate_spec=order.rate_spec,
        rate_base=quote.base,
        rate_quote=quote.quote,
        rate_value=quote.value,
        rate_locked_at=now,
        whole=proposal.whole,
        expires_at=now + PROPOSAL_TTL,
    )
    give = DealLeg(
        id=uuid.uuid4(),
        payer_id=author.id,
        payee_id=proposer.id,
        currency=order.give_currency,
        country=order.give_country,
        amount=proposal.amount,
        method=proposal.give_method,
        due_date=proposal.their_due,
    )
    take = DealLeg(
        id=uuid.uuid4(),
        payer_id=proposer.id,
        payee_id=author.id,
        currency=want.currency,
        country=want.country,
        amount=counter,
        method=proposal.counter_method,
        due_date=proposal.my_due,
    )
    take.seq, give.seq = (1, 2) if proposal.first == "proposer" else (2, 1)
    await _fill_details(db, give, proposer.id, proposal.receive_with, keys)
    deal.legs = sorted([give, take], key=lambda leg: leg.seq)
    db.add(deal)
    await db.flush()
    await start(db, deal, proposer.id, amount=str(give.amount), counter=str(take.amount))
    _tell(
        db,
        deal,
        author.id,
        "deal.proposed",
        proposer,
        amount=str(give.amount),
        currency=give.currency,
        counter_amount=str(take.amount),
        counter_currency=take.currency,
    )
    return deal


async def accept(
    db: AsyncSession, actor: User, deal_id: uuid.UUID, receipt: Receipt, keys: Keys | None
) -> Deal:
    """The author takes the proposal: its amount leaves the order's remainder (FR-2.3)."""
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.PROPOSED)
    _mine(actor.id == deal.acceptor_id)
    if datetime.now(UTC) >= deal.expires_at:
        raise _refuse("deal.expired")
    take = next(leg for leg in deal.legs if leg.payee_id == deal.acceptor_id)
    await _fill_details(db, take, actor.id, receipt.receive_with, keys)

    order = await db.scalar(select(Order).where(Order.id == deal.order_id).with_for_update())
    if order is None or order.status != OrderStatus.OPEN:
        raise _refuse("order.not_open")
    amount = give_amount(deal)
    if amount > order.amount_remaining:
        raise _refuse("order.insufficient_remaining")
    order.amount_remaining -= amount
    if order.amount_remaining < order.amount_min:
        order.status = OrderStatus.FULFILLED

    deal.accepted_at = datetime.now(UTC)
    await record(db, deal, actor.id, "accepted", DealStatus.ACCEPTED)
    # Whatever the remainder can no longer cover goes (Q-E2).
    await cancel_on_order(db, order, actor.id, above=order.amount_remaining, keep=deal.id)
    proposer = await db.get(User, deal.proposer_id)
    if proposer is not None:
        _tell(db, deal, proposer.id, "deal.accepted", actor)
    return deal


async def decline(db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.PROPOSED)
    _mine(actor.id == deal.acceptor_id)
    await record(db, deal, actor.id, "declined", DealStatus.CANCELLED)
    _tell(db, deal, deal.proposer_id, "deal.declined", actor)
    return deal


async def withdraw(db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.PROPOSED)
    _mine(actor.id == deal.proposer_id)
    await record(db, deal, actor.id, "withdrawn", DealStatus.CANCELLED)
    _tell(db, deal, deal.acceptor_id, "deal.withdrawn", actor)
    return deal


async def mark_sent(db: AsyncSession, actor: User, deal_id: uuid.UUID, seq: int) -> Deal:
    """«Отправлено» on a leg, by its payer. Leg 2 waits for leg 1 to be received (Q-B1)."""
    deal = await _lock(db, actor.id, deal_id)
    leg = _leg(deal, seq)
    _require(deal, DealStatus.ACCEPTED if seq == 1 else DealStatus.LEG1_RECEIVED)
    _mine(actor.id == leg.payer_id)
    leg.sent_at = datetime.now(UTC)
    to = DealStatus.LEG1_SENT if seq == 1 else DealStatus.LEG2_SENT
    await record(db, deal, actor.id, "sent", to, seq=seq)
    _tell(db, deal, leg.payee_id, "deal.sent", actor, amount=str(leg.amount), currency=leg.currency)
    return deal


async def mark_received(db: AsyncSession, actor: User, deal_id: uuid.UUID, seq: int) -> Deal:
    """«Получено» on a leg, by its payee. The second one settles the deal."""
    deal = await _lock(db, actor.id, deal_id)
    leg = _leg(deal, seq)
    _require(deal, DealStatus.LEG1_SENT if seq == 1 else DealStatus.LEG2_SENT)
    _mine(actor.id == leg.payee_id)
    leg.received_at = datetime.now(UTC)
    to = DealStatus.LEG1_RECEIVED if seq == 1 else DealStatus.SETTLED
    if to in TERMINAL:
        deal.cancel_requested_by = None
    await record(db, deal, actor.id, "received", to, seq=seq)
    kind: NotificationType = "deal.received" if seq == 1 else "deal.settled"
    _tell(db, deal, leg.payer_id, kind, actor, amount=str(leg.amount), currency=leg.currency)
    return deal


async def cancel(db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
    """Before the first «Отправлено», either side cancels alone (FR-4.5)."""
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.ACCEPTED)
    await record(db, deal, actor.id, "cancelled", DealStatus.CANCELLED)
    await _restore(db, deal)
    _tell(db, deal, _other(deal, actor.id), "deal.cancelled", actor)
    return deal


async def request_cancel(db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
    """After the first «Отправлено», a cancel needs the other side (FR-4.5). Its screens
    and messages come with slice 4."""
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, *AFTER_FIRST_SENT)
    if deal.cancel_requested_by is not None:
        raise _refuse("deal.cancel_pending")
    deal.cancel_requested_by = actor.id
    await record(db, deal, actor.id, "cancel_requested")
    return deal


async def answer_cancel(
    db: AsyncSession, actor: User, deal_id: uuid.UUID, *, approve: bool
) -> Deal:
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, *AFTER_FIRST_SENT)
    if deal.cancel_requested_by is None:
        raise _refuse("deal.no_cancel_request")
    _mine(actor.id != deal.cancel_requested_by)
    deal.cancel_requested_by = None
    if approve:
        await record(db, deal, actor.id, "cancel_approved", DealStatus.CANCELLED)
        await _restore(db, deal)
        _tell(db, deal, _other(deal, actor.id), "deal.cancelled", actor)
    else:
        # A declined request changes nothing else (Q-B1).
        await record(db, deal, actor.id, "cancel_rejected")
    return deal


async def dispute(db: AsyncSession, actor: User, deal_id: uuid.UUID, note: str) -> Deal:
    """«Проблема»: either side, from any active state, with a word on what went wrong.

    It freezes the deal until both agree how it ended (FR-4.6). Its screens and messages
    come with slice 4.
    """
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, *ACTIVE)
    deal.disputed_by = actor.id
    deal.dispute_note = note
    deal.cancel_requested_by = None
    await record(db, deal, actor.id, "disputed", DealStatus.DISPUTED, note=note)
    return deal


async def resolve(
    db: AsyncSession,
    actor: User,
    deal_id: uuid.UUID,
    outcome: Literal["settled", "cancelled"],
) -> Deal:
    """One side proposes how a dispute ended; the other confirms the same outcome (FR-4.6)."""
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.DISPUTED)
    if deal.resolution == outcome and deal.resolution_by not in (None, actor.id):
        deal.resolution = None
        deal.resolution_by = None
        await record(db, deal, actor.id, "resolved", DealStatus(outcome), outcome=outcome)
        if outcome == "cancelled":
            await _restore(db, deal)
        return deal
    if deal.resolution == outcome and deal.resolution_by == actor.id:
        return deal  # proposed already
    deal.resolution = outcome
    deal.resolution_by = actor.id
    await record(db, deal, actor.id, "resolution_proposed", outcome=outcome)
    return deal


async def expire_due(db: AsyncSession, now: datetime | None = None) -> int:
    """Proposals left unanswered for 48 h expire: the one timed transition (§5, FR-4.4).

    The sweep that calls this arrives with slice 5 (ADR-0005).
    """
    due = list(
        await db.scalars(
            select(Deal)
            .where(
                Deal.status == DealStatus.PROPOSED, Deal.expires_at <= (now or datetime.now(UTC))
            )
            .with_for_update(skip_locked=True)
        )
    )
    for deal in due:
        await record(db, deal, None, "expired", DealStatus.EXPIRED)
        author = await db.get(User, deal.acceptor_id)
        if author is not None:
            _tell(db, deal, deal.proposer_id, "deal.expired", author)
    return len(due)


async def get(db: AsyncSession, viewer: uuid.UUID, deal_id: uuid.UUID) -> Deal:
    deal = await db.scalar(
        select(Deal).where(
            Deal.id == deal_id, or_(Deal.proposer_id == viewer, Deal.acceptor_id == viewer)
        )
    )
    if deal is None:
        raise _refuse("deal.not_found", 404)
    return deal


async def mine(
    db: AsyncSession,
    viewer: uuid.UUID,
    scope: Literal["active", "history"],
    order_id: uuid.UUID | None = None,
) -> list[Deal]:
    """The viewer's deals: open ones, newest first, or closed ones (FR-6.3 without CSV)."""
    query = select(Deal).where(or_(Deal.proposer_id == viewer, Deal.acceptor_id == viewer))
    if order_id is not None:
        query = query.where(Deal.order_id == order_id)
    states = OPEN_STATES if scope == "active" else TERMINAL
    query = query.where(Deal.status.in_([state.value for state in states]))
    return list(await db.scalars(query.order_by(Deal.created_at.desc())))


async def journal(db: AsyncSession, deal: Deal) -> list[Event]:
    return list(await db.scalars(select(Event).where(Event.deal_id == deal.id).order_by(Event.id)))
