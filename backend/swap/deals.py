"""Deals: the state machine, the only code that changes a deal (ADR-0002, ADR-0018, ADR-0024).

Every action locks the deal, checks that the actor may take it from the deal's state,
applies it, and journals it through swap/journal.py in the same transaction. A
stranger to a deal gets 404 for everything, as for a deal that doesn't exist. A wrong
state is 409 `deal.invalid_transition`; the other side's move is 403 `deal.not_your_move`.

    proposed ─accept→ accepted ── each leg on its own, in any order (QUESTIONS H2):
        │                │          «Отправлено» by its payer, «Получено» by its payee;
        │ decline,       │          the second «Получено» settles ─────────────→ settled
        │ withdraw,      │ cancel, while nothing has moved
        │ expire         ↓
        ↓            cancelled ←─ cancel request, approved, once something has moved
     cancelled/          ↑
     expired         disputed ←── «Проблема» from accepted
                         └── resolved as settled or cancelled, by one side, confirmed by the other
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import ColumnElement, and_, exists, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from swap import orders
from swap.deeplinks import target
from swap.erasure import erase_deal, erase_order_if_bare
from swap.errors import DomainError
from swap.journal import TERMINAL, record, start
from swap.market import Market, lock
from swap.models import (
    Deal,
    DealLeg,
    DealStatus,
    Event,
    Order,
    OrderStatus,
    PaymentKind,
    User,
)
from swap.money import Asset, Money
from swap.notifications import NotificationType, notify
from swap.proposals import cancel_on_order, give_amount
from swap.rates import convert, parse_spec
from swap.users import person_label

PROPOSAL_TTL = timedelta(hours=48)
OPEN_STATES = frozenset({DealStatus.PROPOSED, DealStatus.ACCEPTED, DealStatus.DISPUTED})
# The proposer's own transfer is leg 1, the author's leg 2: an order of them no longer.
PROPOSERS, AUTHORS = 1, 2


class Proposal(BaseModel):
    """What the proposal form sends (FR-4.1). Amounts are in the order's own currency."""

    model_config = ConfigDict(extra="forbid")

    amount: Money
    want_currency: Asset
    # Round the counter-amount to whole units, for cash (Q-B4).
    whole: bool = False
    # How the author pays out: one of the order's own ways.
    give_method: PaymentKind
    # How the proposer pays the other currency, «в ответ GEL наличными»: one of the ways
    # the order's author can be paid (QUESTIONS F2).
    counter_method: PaymentKind
    # Anything else, such as which bank: the parties settle the details themselves
    # (QUESTIONS G3).
    note: str | None = Field(default=None, max_length=500)


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


def kept_by(viewer: uuid.UUID) -> ColumnElement[bool]:
    """The deals `viewer` has and hasn't deleted (QUESTIONS J3, ADR-0030): a proposer's
    unless they deleted it; an author's unless they deleted its order and it is over."""
    author_deleted = exists().where(Order.id == Deal.order_id, Order.deleted_at.is_not(None))
    over = Deal.status.in_([state.value for state in TERMINAL])
    return or_(
        and_(Deal.proposer_id == viewer, Deal.proposer_deleted_at.is_(None)),
        and_(Deal.acceptor_id == viewer, not_(and_(author_deleted, over))),
    )


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


def _moved(deal: Deal) -> bool:
    """Whether any money has been marked as moving: from then a cancel needs both (FR-4.5)."""
    return any(leg.sent_at is not None or leg.received_at is not None for leg in deal.legs)


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
        .where(Deal.id == deal_id, kept_by(me))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if deal is None:
        raise _refuse("deal.not_found", 404)
    return deal


async def _restore(db: AsyncSession, deal: Deal) -> None:
    """An accepted deal that ends cancelled gives its amount back to the order (FR-2.3)."""
    order = await db.scalar(select(Order).where(Order.id == deal.order_id).with_for_update())
    if order is None:  # pragma: no cover - the foreign key guarantees the row
        return
    order.amount_remaining = min(order.amount_max, order.amount_remaining + give_amount(deal))
    fits = order.amount_remaining >= orders.smallest_deal(order)
    # A deleted order stays gone (QUESTIONS F6).
    if order.status == OrderStatus.FULFILLED and fits and order.deleted_at is None:
        order.status = OrderStatus.OPEN


async def propose(
    db: AsyncSession, proposer: User, order_id: uuid.UUID, proposal: Proposal, market: Market
) -> Deal:
    """A deal proposed on an order the proposer can see (FR-4.1)."""
    order, author = await orders.get(db, proposer.id, order_id, to_propose=True)
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
    if proposal.counter_method not in order.receive_methods:
        raise _refuse("deal.method_not_accepted", 422)

    # The wanted currency's own rate, the author's or the market's of this moment, locked
    # here (Q-B3, QUESTIONS G2, J1).
    spec, found = await lock(parse_spec(want.rate_spec), order.give_currency, want.currency, market)
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
        rate_spec=spec.model_dump(mode="json"),
        rate_base=quote.base,
        rate_quote=quote.quote,
        rate_value=quote.value,
        rate_locked_at=now,
        rate_source="coinbase" if found else None,
        rate_fetched_at=found.fetched_at if found else None,
        whole=proposal.whole,
        expires_at=now + PROPOSAL_TTL,
        note=(proposal.note or "").strip() or None,
    )
    # No order between the transfers, and no dates: the parties settle both (H1).
    take = DealLeg(
        id=uuid.uuid4(),
        seq=PROPOSERS,
        payer_id=proposer.id,
        payee_id=author.id,
        currency=want.currency,
        country=want.country,
        amount=counter,
        method=proposal.counter_method,
    )
    give = DealLeg(
        id=uuid.uuid4(),
        seq=AUTHORS,
        payer_id=author.id,
        payee_id=proposer.id,
        currency=order.give_currency,
        country=order.give_country,
        amount=proposal.amount,
        method=proposal.give_method,
    )
    deal.legs = [take, give]
    db.add(deal)
    await db.flush()
    await start(db, deal, proposer.id, amount=str(give.amount), counter=str(take.amount))
    _tell(
        db,
        deal,
        author.id,
        "deal.proposed",
        proposer,
        number=str(order.number),
        amount=str(give.amount),
        currency=give.currency,
        counter_amount=str(take.amount),
        counter_currency=take.currency,
    )
    return deal


async def accept(db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
    """The author takes the proposal: its amount leaves the order's remainder (FR-2.3)."""
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.PROPOSED)
    _mine(actor.id == deal.acceptor_id)
    if datetime.now(UTC) >= deal.expires_at:
        raise _refuse("deal.expired")

    order = await db.scalar(select(Order).where(Order.id == deal.order_id).with_for_update())
    if order is None or order.status != OrderStatus.OPEN:
        raise _refuse("order.not_open")
    amount = give_amount(deal)
    if amount > order.amount_remaining:
        raise _refuse("order.insufficient_remaining")
    order.amount_remaining -= amount
    # Used up once no deal fits: below the minimum, or nothing left at all (Q-B5, F4).
    if order.amount_remaining < orders.smallest_deal(order):
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
    """«Отправлено» on a leg, by its payer, whenever they pay while the deal runs (H2).

    The deal stays accepted; the journal says which transfer moved (H3).
    """
    deal = await _lock(db, actor.id, deal_id)
    leg = _leg(deal, seq)
    _require(deal, DealStatus.ACCEPTED)
    _mine(actor.id == leg.payer_id)
    if leg.sent_at is not None or leg.received_at is not None:
        raise _refuse("deal.invalid_transition")
    leg.sent_at = datetime.now(UTC)
    await record(db, deal, actor.id, "sent", seq=seq)
    _tell(db, deal, leg.payee_id, "deal.sent", actor, amount=str(leg.amount), currency=leg.currency)
    return deal


async def mark_received(db: AsyncSession, actor: User, deal_id: uuid.UUID, seq: int) -> Deal:
    """«Получено» on a leg, by its payee, as the money arrives, marked as sent or not (H2).
    The receipt that leaves nothing outstanding settles the deal."""
    deal = await _lock(db, actor.id, deal_id)
    leg = _leg(deal, seq)
    _require(deal, DealStatus.ACCEPTED)
    _mine(actor.id == leg.payee_id)
    if leg.received_at is not None:
        raise _refuse("deal.invalid_transition")
    now = datetime.now(UTC)
    # Money that arrived was sent, whether or not its payer said so (ck_deal_legs_sent_first).
    leg.sent_at = leg.sent_at or now
    leg.received_at = now
    settled = all(each.received_at is not None for each in deal.legs)
    if settled:
        deal.cancel_requested_by = None
    await record(db, deal, actor.id, "received", DealStatus.SETTLED if settled else None, seq=seq)
    kind: NotificationType = "deal.settled" if settled else "deal.received"
    _tell(db, deal, leg.payer_id, kind, actor, amount=str(leg.amount), currency=leg.currency)
    return deal


async def cancel(db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
    """While nothing has moved, either side cancels alone (FR-4.5)."""
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.ACCEPTED)
    if _moved(deal):
        raise _refuse("deal.invalid_transition")
    await record(db, deal, actor.id, "cancelled", DealStatus.CANCELLED)
    await _restore(db, deal)
    _tell(db, deal, _other(deal, actor.id), "deal.cancelled", actor)
    return deal


async def request_cancel(db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
    """Once something has moved, a cancel needs the other side (FR-4.5). Its screens and
    messages come with slice 4."""
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.ACCEPTED)
    if not _moved(deal):
        raise _refuse("deal.invalid_transition")
    if deal.cancel_requested_by is not None:
        raise _refuse("deal.cancel_pending")
    deal.cancel_requested_by = actor.id
    await record(db, deal, actor.id, "cancel_requested")
    return deal


async def answer_cancel(
    db: AsyncSession, actor: User, deal_id: uuid.UUID, *, approve: bool
) -> Deal:
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.ACCEPTED)
    if not _moved(deal):
        raise _refuse("deal.invalid_transition")
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
    """«Проблема»: either side, while the deal runs, with a word on what went wrong.

    It freezes the deal until both agree how it ended (FR-4.6). Its screens and messages
    come with slice 4.
    """
    deal = await _lock(db, actor.id, deal_id)
    _require(deal, DealStatus.ACCEPTED)
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
    deal = await db.scalar(select(Deal).where(Deal.id == deal_id, kept_by(viewer)))
    if deal is None:
        raise _refuse("deal.not_found", 404)
    return deal


async def mine(
    db: AsyncSession,
    viewer: uuid.UUID,
    scope: Literal["active", "history", "all"],
    order_id: uuid.UUID | None = None,
) -> list[Deal]:
    """The viewer's deals, newest first: open ones, closed ones (FR-6.3 without CSV), or
    both, as an order's card lists them."""
    query = select(Deal).where(kept_by(viewer))
    if order_id is not None:
        query = query.where(Deal.order_id == order_id)
    if scope != "all":
        states = OPEN_STATES if scope == "active" else TERMINAL
        query = query.where(Deal.status.in_([state.value for state in states]))
    return list(await db.scalars(query.order_by(Deal.created_at.desc())))


async def delete(db: AsyncSession, actor: User, deal_id: uuid.UUID) -> None:
    """A participant deletes their own finished deal, for themselves alone (QUESTIONS J3).

    The author deletes whole orders instead. Once the author has deleted this one's order,
    nobody keeps the deal, and it is erased (ADR-0030).
    """
    deal = await _lock(db, actor.id, deal_id)
    if actor.id != deal.proposer_id:
        raise _refuse("deal.delete_with_order")
    if deal.status not in TERMINAL:
        raise _refuse("deal.running")
    await delete_for_proposer(db, deal)


async def delete_order(db: AsyncSession, actor: uuid.UUID, order_id: uuid.UUID) -> None:
    """«Удалить у себя» on an order's card, for oneself alone (QUESTIONS J3, L4). Its author
    deletes it with all its deals (`orders.delete`). Whoever proposed on it deletes all
    their own deals on it at once, once every one of them is over (ADR-0030).
    """
    author = await db.scalar(select(Order.author_id).where(Order.id == order_id))
    if author == actor:
        await orders.delete(db, actor, order_id)
        return
    mine = list(
        await db.scalars(
            select(Deal)
            .where(
                Deal.order_id == order_id,
                Deal.proposer_id == actor,
                Deal.proposer_deleted_at.is_(None),
            )
            .with_for_update()
        )
    )
    if not mine:
        # The same answer whether it doesn't exist or holds nothing of theirs.
        raise _refuse("order.not_found", 404)
    if any(deal.status not in TERMINAL for deal in mine):
        raise _refuse("deal.running")
    for deal in mine:
        await delete_for_proposer(db, deal)


async def delete_for_proposer(db: AsyncSession, deal: Deal) -> None:
    """Mark a finished deal deleted by its proposer, and erase it if its author has deleted
    the order already (ADR-0030). The caller has checked it may."""
    deal.proposer_deleted_at = datetime.now(UTC)
    order = await db.scalar(select(Order).where(Order.id == deal.order_id).with_for_update())
    if order is not None and order.deleted_at is not None:
        await erase_deal(db, deal)
        await erase_order_if_bare(db, order)


async def journal(db: AsyncSession, deal: Deal) -> list[Event]:
    return list(await db.scalars(select(Event).where(Event.deal_id == deal.id).order_by(Event.id)))
