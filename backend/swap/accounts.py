"""Deleting all of one's history, or one's account (QUESTIONS K2, Q-B10; ADR-0032).

All history means every finished deal and order deleted for oneself at once, as one by
one (ADR-0030): what both sides have deleted is erased. What still runs stays.

An account goes only once none of its deals runs. Its proposals are taken back, its open
orders closed, its history deleted, and its links, invites, sessions, mutes and messages
removed. The row stays, scrubbed, as «Удалённый участник», because others may keep
deals with it. The same Telegram account starting Swap again is someone new.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from swap import deals, orders
from swap.errors import DomainError
from swap.journal import TERMINAL
from swap.links import involves
from swap.models import (
    AuthSession,
    Deal,
    DealStatus,
    Invite,
    Link,
    Mute,
    Notification,
    Order,
    OrderStatus,
    User,
)
from swap.proposals import cancel_by

RUNNING = (DealStatus.PROPOSED, DealStatus.ACCEPTED, DealStatus.DISPUTED)


@dataclass(frozen=True, slots=True)
class Deleted:
    """What «Удалить всю историю» deleted, and how much still runs and stays."""

    deals: int
    orders: int
    running: int


async def delete_history(db: AsyncSession, me: User) -> Deleted:
    """Every finished deal and order of `me` deleted for them, as each would be alone."""
    finished = list(
        await db.scalars(
            select(Deal)
            .where(
                Deal.proposer_id == me.id,
                Deal.proposer_deleted_at.is_(None),
                Deal.status.in_([state.value for state in TERMINAL]),
            )
            .with_for_update()
        )
    )
    for deal in finished:
        await deals.delete_for_proposer(db, deal)
    done = 0
    for order in await db.scalars(
        select(Order)
        .where(
            Order.author_id == me.id,
            Order.deleted_at.is_(None),
            Order.status != OrderStatus.OPEN,
        )
        .with_for_update()
    ):
        done += int(await orders.delete_finished(db, order))
    running_deals = await db.scalar(
        select(func.count())
        .select_from(Deal)
        .where(
            or_(Deal.proposer_id == me.id, Deal.acceptor_id == me.id),
            Deal.status.in_([state.value for state in RUNNING]),
        )
    )
    open_orders = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.author_id == me.id, Order.status == OrderStatus.OPEN)
    )
    return Deleted(len(finished), done, (running_deals or 0) + (open_orders or 0))


async def delete_account(db: AsyncSession, me: User) -> None:
    """Refused while a deal runs; otherwise everything of `me` goes, but the scrubbed row."""
    accepted = await db.scalar(
        select(func.count())
        .select_from(Deal)
        .where(
            or_(Deal.proposer_id == me.id, Deal.acceptor_id == me.id),
            Deal.status.in_([DealStatus.ACCEPTED.value, DealStatus.DISPUTED.value]),
        )
    )
    if accepted:
        raise DomainError(409, "account.deals_running")
    await cancel_by(db, me.id)
    for order_id in list(
        await db.scalars(
            select(Order.id).where(Order.author_id == me.id, Order.status == OrderStatus.OPEN)
        )
    ):
        # Closing cancels the proposals on it, and tells their proposers (Q-E2).
        await orders.close(db, me.id, order_id)
    await delete_history(db, me)
    await db.execute(delete(Link).where(involves(me.id)))
    await db.execute(delete(Invite).where(Invite.created_by == me.id))
    await db.execute(delete(AuthSession).where(AuthSession.user_id == me.id))
    await db.execute(delete(Mute).where(or_(Mute.user_id == me.id, Mute.muted_id == me.id)))
    await db.execute(delete(Notification).where(Notification.recipient_id == me.id))
    me.telegram_id = None
    me.first_name = ""
    me.last_name = None
    me.username = None
    me.photo_url = None
    me.language_code = None
    me.locale = None
    me.tz = None
    me.can_message = False
    me.notifications_off = True
    me.muted_kinds = []
    me.deleted_at = datetime.now(UTC)
    await db.flush()
