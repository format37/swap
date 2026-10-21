"""The deal journal: every change of a deal is an event, written with the change (ADR-0002).

`record` is the only code that sets a deal's status. It inserts the event first, then
points the deal at it, which is what the `deals_journaled` trigger checks (ADR-0018).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from swap.models import Deal, DealStatus, Event

TERMINAL = frozenset({DealStatus.SETTLED, DealStatus.CANCELLED, DealStatus.EXPIRED})


async def record(
    db: AsyncSession,
    deal: Deal,
    actor: uuid.UUID | None,
    kind: str,
    to: DealStatus | None = None,
    **details: Any,
) -> Event:
    """Journal `kind` on `deal` and, with `to`, move it there, in the caller's transaction.

    `actor` is None for the system, as for an expiry.
    """
    target = to or DealStatus(deal.status)
    event = Event(
        deal_id=deal.id,
        actor_id=actor,
        type=kind,
        payload={"from": deal.status, "to": target.value, **details},
    )
    db.add(event)
    # The event must exist before the deal points at it.
    await db.flush()
    deal.status = target
    deal.last_event_id = event.id
    if target in TERMINAL and deal.closed_at is None:
        deal.closed_at = datetime.now(UTC)
    await db.flush()
    return event


async def start(db: AsyncSession, deal: Deal, actor: uuid.UUID, **details: Any) -> Event:
    """Journal a new deal's proposal. A deal is born `proposed`; the trigger allows nothing else."""
    event = Event(
        deal_id=deal.id,
        actor_id=actor,
        type="proposed",
        payload={"from": None, "to": DealStatus.PROPOSED.value, **details},
    )
    db.add(event)
    await db.flush()
    deal.last_event_id = event.id
    await db.flush()
    return event
