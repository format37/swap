"""Pending proposals that someone's action leaves without a footing (Q-B9, Q-E2).

Breaking a link cancels the pair's proposals. An order that closes, fills up or expires
cancels its proposals, and so does an accepted deal for every proposal the remainder can
no longer cover. Each is journaled with its reason. None is a timer of its own: they
follow from someone's action or from the order's own end date.
"""

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from swap.deeplinks import target
from swap.journal import record
from swap.models import Deal, DealStatus, Order, User
from swap.notifications import notify
from swap.users import person_label

type Reason = Literal["link_removed", "order_closed", "order_short", "account_deleted"]
# A break tells nobody (ADR-0012), nor does someone leaving Swap (QUESTIONS K2).
QUIET: frozenset[Reason] = frozenset({"link_removed", "account_deleted"})


def give_amount(deal: Deal) -> Decimal:
    """What the deal takes from its order: the leg the order's author pays."""
    return next(leg.amount for leg in deal.legs if leg.payer_id == deal.acceptor_id)


async def _cancel(
    db: AsyncSession, deals: Sequence[Deal], actor: uuid.UUID | None, reason: Reason
) -> None:
    for deal in deals:
        await record(db, deal, actor, "cancelled", DealStatus.CANCELLED, reason=reason)
        if reason not in QUIET:
            author = await db.get(User, deal.acceptor_id)
            notify(
                db,
                deal.proposer_id,
                "deal.proposal_closed",
                target=target("deal", deal.id),
                name=person_label(author) if author else "",
            )


async def cancel_between(db: AsyncSession, a: uuid.UUID, b: uuid.UUID, actor: uuid.UUID) -> None:
    """The pair's link is gone, so are its unanswered proposals (Q-B9)."""
    deals = await db.scalars(
        select(Deal)
        .where(
            Deal.status == DealStatus.PROPOSED,
            or_(
                and_(Deal.proposer_id == a, Deal.acceptor_id == b),
                and_(Deal.proposer_id == b, Deal.acceptor_id == a),
            ),
        )
        .with_for_update()
    )
    await _cancel(db, list(deals), actor, "link_removed")


async def cancel_by(db: AsyncSession, proposer: uuid.UUID) -> None:
    """Someone leaving Swap takes back every proposal they made (Q-B10, QUESTIONS K2)."""
    deals = await db.scalars(
        select(Deal)
        .where(Deal.proposer_id == proposer, Deal.status == DealStatus.PROPOSED)
        .with_for_update()
    )
    await _cancel(db, list(deals), proposer, "account_deleted")


async def cancel_on_order(
    db: AsyncSession,
    order: Order,
    actor: uuid.UUID | None,
    *,
    above: Decimal | None = None,
    keep: uuid.UUID | None = None,
) -> None:
    """Cancel the order's proposals: all of them, or those for more than `above` (Q-E2)."""
    deals = await db.scalars(
        select(Deal)
        .where(Deal.order_id == order.id, Deal.status == DealStatus.PROPOSED, Deal.id != keep)
        .with_for_update()
    )
    if above is None:
        doomed = list(deals)
        reason: Reason = "order_closed"
    else:
        doomed = [deal for deal in deals if give_amount(deal) > above]
        reason = "order_short"
    await _cancel(db, doomed, actor, reason)
