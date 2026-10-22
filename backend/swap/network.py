"""The network: how many handshakes over active links lie between two people (ADR-0028).

Your links are 1 handshake away, their links 2, and so on. Reach and the feed's filter
only tell 1, 2, 3 and "any chain at all" apart, so the walk caps depth at FAR, which
stands for four and more.

Visibility asks in SQL, through `distances`, so it composes with the feeds' queries.
Chains and rings are for showing, and come from `Graph`, a breadth-first walk over the
same links in Python. A test holds the two to the same answers.
"""

import uuid
from collections import deque
from collections.abc import Iterable

from sqlalchemy import CTE, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from swap.links import involves, other_side_of
from swap.models import Link, LinkStatus

# Four handshakes or more: past three, all that matters is that a chain exists.
FAR = 4


def distances(me: uuid.UUID) -> CTE:
    """Everyone a chain of active links joins to `me`, as (user_id, depth) rows.

    A person may come up at several depths, `me` among them; their distance is the least.
    Postgres's UNION drops rows it has produced already, and with depth capped at FAR a
    person yields at most four rows, so the walk ends however the links loop.
    """
    ring = (
        select(other_side_of(me).label("user_id"), literal(1).label("depth"))
        .where(involves(me), Link.status == LinkStatus.ACTIVE)
        .cte(recursive=True)
    )
    # Anonymous, so two walks can share one statement.
    known = ring.alias()
    link = aliased(Link)
    further = select(
        case((link.user_lo_id == known.c.user_id, link.user_hi_id), else_=link.user_lo_id),
        func.least(known.c.depth + 1, FAR),
    ).where(
        or_(link.user_lo_id == known.c.user_id, link.user_hi_id == known.c.user_id),
        link.status == LinkStatus.ACTIVE,
    )
    return ring.union(further)


class Graph:
    """Active links as neighbours, for walking breadth first."""

    def __init__(self, pairs: Iterable[tuple[uuid.UUID, uuid.UUID]]) -> None:
        self.neighbours: dict[uuid.UUID, set[uuid.UUID]] = {}
        for a, b in pairs:
            self.neighbours.setdefault(a, set()).add(b)
            self.neighbours.setdefault(b, set()).add(a)

    @classmethod
    async def load(cls, db: AsyncSession) -> "Graph":
        rows = await db.execute(
            select(Link.user_lo_id, Link.user_hi_id).where(Link.status == LinkStatus.ACTIVE)
        )
        return cls((lo, hi) for lo, hi in rows)

    def walk(self, start: uuid.UUID) -> dict[uuid.UUID, uuid.UUID | None]:
        """Everyone reachable from `start`, each with whom the walk came through."""
        came_from: dict[uuid.UUID, uuid.UUID | None] = {start: None}
        queue = deque([start])
        while queue:
            here = queue.popleft()
            # Sorted, so the same links always give the same chain.
            for there in sorted(self.neighbours.get(here, ())):
                if there not in came_from:
                    came_from[there] = here
                    queue.append(there)
        return came_from

    def rings(self, start: uuid.UUID) -> dict[uuid.UUID, int]:
        """Everyone reachable from `start` but `start`, with their distance capped at FAR."""
        came_from = self.walk(start)
        depth: dict[uuid.UUID, int] = {start: 0}
        for person, previous in came_from.items():
            if previous is not None:
                depth[person] = depth[previous] + 1
        del depth[start]
        return {person: min(steps, FAR) for person, steps in depth.items()}

    def chain(self, start: uuid.UUID, end: uuid.UUID) -> list[uuid.UUID] | None:
        """The people between `start` and `end` on one shortest chain, from `start`'s side:
        [] for a direct link, None when no chain joins them."""
        came_from = self.walk(start)
        if end not in came_from or end == start:
            return None
        between: list[uuid.UUID] = []
        step = came_from[end]
        while step is not None and step != start:
            between.append(step)
            step = came_from[step]
        return between[::-1]
