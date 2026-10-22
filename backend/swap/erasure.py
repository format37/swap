"""Erasing what everyone it belongs to has deleted (QUESTIONS J3, ADR-0030).

A deal goes once its proposer has deleted it and its author has deleted its order. Its
legs, its journal and the notifications that open it go with it. An order goes once its
author has deleted it and none of its deals remain. Each happens in the transaction of
the deletion that completes it, so there is no sweep and nothing waits half done.
"""

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from swap.deeplinks import target
from swap.models import Deal, Notification, Order


async def erase_deal(db: AsyncSession, deal: Deal) -> None:
    """The deal, its legs and its journal, and every message that opens it."""
    await db.execute(delete(Notification).where(Notification.target == target("deal", deal.id)))
    # Its legs go with it here; its journal in the database, which allows it only now.
    await db.delete(deal)
    await db.flush()


async def erase_order_if_bare(db: AsyncSession, order: Order) -> bool:
    """The order, once its author has deleted it and none of its deals remain."""
    if order.deleted_at is None or await db.scalar(
        select(exists().where(Deal.order_id == order.id))
    ):
        return False
    await db.execute(delete(Notification).where(Notification.target == target("order", order.id)))
    await db.delete(order)
    await db.flush()
    return True
