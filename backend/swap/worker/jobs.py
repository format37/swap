"""Scheduled jobs. Each is an idempotent sweep over database state (ADR-0005)."""

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from swap.db import Sessionmaker
from swap.models import ServiceHeartbeat


async def beat(sessionmaker: Sessionmaker) -> None:
    """The heartbeat api's /healthz reports."""
    statement = insert(ServiceHeartbeat).values(name="worker", beat_at=func.now())
    statement = statement.on_conflict_do_update(
        index_elements=[ServiceHeartbeat.name], set_={"beat_at": func.now()}
    )
    async with sessionmaker() as db:
        await db.execute(statement)
        await db.commit()
