"""`/healthz`: the api is up, the database answers, and how long ago the worker beat."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from swap.api.deps import Db
from swap.api.errors import ApiError, Problem
from swap.models import ServiceHeartbeat

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    # Seconds since the worker's last heartbeat; null if it has never beaten.
    worker_heartbeat_age_s: float | None


@router.get("/healthz", responses={503: {"model": Problem}})
async def healthz(db: Db) -> Health:
    try:
        now = await db.scalar(select(func.now()))
        beat = await db.scalar(
            select(ServiceHeartbeat.beat_at).where(ServiceHeartbeat.name == "worker")
        )
    except (SQLAlchemyError, OSError) as exc:
        raise ApiError(503, "database_unavailable") from exc
    age = (now - beat).total_seconds() if now is not None and beat is not None else None
    return Health(worker_heartbeat_age_s=age)
