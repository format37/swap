"""Sharing an order: an invite that carries it (QUESTIONS O1, ADR-0041).

Its author shares a one-time invite link with the order in words. Whoever opens it and
already sees the order is taken to it. Anyone else gets a link request from the author,
as with any invite (ADR-0012), and sees the order once they accept. At reach 0 they are
put on its list too, since its author chose to show it to them.
"""

import uuid
from datetime import timedelta

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from swap import links
from swap.errors import DomainError
from swap.links import Opened, OpenedInvite
from swap.models import Invite, Order, OrderVisibility, User
from swap.orders import current, open_to


async def share(
    db: AsyncSession, author: User, order_id: uuid.UUID, ttl: timedelta
) -> tuple[Invite, str]:
    """A new invite carrying the author's open order, and its token."""
    order = await db.scalar(
        select(Order).where(
            Order.id == order_id, Order.author_id == author.id, Order.deleted_at.is_(None)
        )
    )
    if order is None:
        # The same answer whether it doesn't exist or isn't this author's.
        raise DomainError(404, "order.not_found")
    if not await db.scalar(select(exists().where(Order.id == order.id, current()))):
        raise DomainError(409, "order.not_open")
    return await links.create_invite(db, author.id, ttl, order_id=order.id)


async def _sees(db: AsyncSession, viewer: uuid.UUID, order: Order) -> bool:
    return bool(await db.scalar(select(exists().where(Order.id == order.id, open_to(viewer)))))


async def open_invite(db: AsyncSession, invitee: User, token: str) -> OpenedInvite:
    """What /start inv_<token> does: a plain invite links (ADR-0012), and one that carries
    an order also shows it, linking first only if the invitee can't see it yet."""
    claimed = await links.claim_invite(db, invitee, token)
    if isinstance(claimed, Opened):
        return OpenedInvite(claimed)
    invite, inviter = claimed
    order = None
    if invite.order_id is not None:
        order = await db.scalar(select(Order).where(Order.id == invite.order_id, current()))
    if order is not None and await _sees(db, invitee.id, order):
        links.spend(invite, invitee)
        return OpenedInvite(Opened.SHARED, inviter, order=order, sees_order=True)

    opened = await links.link_by_invite(db, invite, inviter, invitee)
    if order is None:
        return opened
    if order.reach == 0:
        await db.execute(
            insert(OrderVisibility)
            .values(order_id=order.id, user_id=invitee.id)
            .on_conflict_do_nothing()
        )
    return OpenedInvite(
        opened.outcome, inviter, opened.link, order, await _sees(db, invitee.id, order)
    )


async def shared_order(db: AsyncSession, me: uuid.UUID, other: uuid.UUID) -> Order | None:
    """The open order `other` last shared with `me` by an invite `me` opened: the request
    screen names it, and leads to it once linked."""
    found: Order | None = await db.scalar(
        select(Order)
        .join(Invite, Invite.order_id == Order.id)
        .where(Invite.created_by == other, Invite.used_by == me, current())
        .order_by(Invite.used_at.desc())
        .limit(1)
    )
    return found
