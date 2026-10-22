"""The signed-in user: who they are, their language (ADR-0009) and time zone (Q-B17)."""

import uuid
import zoneinfo
from typing import Self

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field, field_validator

from swap import accounts
from swap.api.deps import CurrentUser, Db
from swap.api.errors import Problem
from swap.i18n import Locale, resolve_locale
from swap.models import NotificationKind, User

router = APIRouter(tags=["me"], responses={401: {"model": Problem}})


class Me(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str | None
    username: str | None
    photo_url: str | None
    # How many different people they settled a deal with (ADR-0029).
    score: int
    # The language to show, already resolved; `locale_chosen` says whether the user
    # picked it or it came from Telegram.
    locale: Locale
    locale_chosen: bool
    # Null until the app sends the device's zone at the first launch.
    tz: str | None
    # What they switched off: everything, or kinds of messages (QUESTIONS K1).
    notifications_off: bool
    muted_kinds: list[NotificationKind]

    @classmethod
    def of(cls, user: User) -> Self:
        return cls(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            photo_url=user.photo_url,
            score=user.score,
            locale=resolve_locale(user.locale, user.language_code),
            locale_chosen=user.locale is not None,
            tz=user.tz,
            notifications_off=user.notifications_off,
            muted_kinds=[NotificationKind(kind) for kind in user.muted_kinds],
        )


class MeUpdate(BaseModel):
    """Only what is sent changes."""

    locale: Locale | None = None
    # An IANA zone, such as Asia/Tbilisi.
    tz: str | None = None
    notifications_off: bool | None = None
    # The whole list of kinds switched off, replacing what was there.
    muted_kinds: list[NotificationKind] | None = Field(
        default=None, max_length=len(NotificationKind)
    )

    @field_validator("tz")
    @classmethod
    def known_zone(cls, value: str | None) -> str | None:
        if value is not None and value not in zoneinfo.available_timezones():
            raise ValueError("not a time zone this server knows")
        return value


@router.get("/me")
async def get_me(user: CurrentUser) -> Me:
    return Me.of(user)


@router.patch("/me", responses={422: {"model": Problem}})
async def update_me(body: MeUpdate, user: CurrentUser, db: Db) -> Me:
    # Stored on the server so the bot writes in the same language as the app.
    if body.locale is not None:
        user.locale = body.locale
    if body.tz is not None:
        user.tz = body.tz
    if body.notifications_off is not None:
        user.notifications_off = body.notifications_off
    if body.muted_kinds is not None:
        user.muted_kinds = list(dict.fromkeys(kind.value for kind in body.muted_kinds))
    await db.commit()
    return Me.of(user)


class HistoryDeleted(BaseModel):
    """What «Удалить всю историю» deleted, and how much still runs and so stays."""

    deals: int
    orders: int
    running: int


@router.delete("/me/history")
async def delete_history(user: CurrentUser, db: Db) -> HistoryDeleted:
    """Every finished deal and order deleted for you at once (QUESTIONS K2, J3)."""
    found = await accounts.delete_history(db, user)
    await db.commit()
    return HistoryDeleted(deals=found.deals, orders=found.orders, running=found.running)


@router.delete("/me", status_code=204, responses={409: {"model": Problem}})
async def delete_me(user: CurrentUser, db: Db) -> Response:
    """Delete the account, once none of its deals runs (Q-B10, QUESTIONS K2)."""
    await accounts.delete_account(db, user)
    await db.commit()
    return Response(status_code=204)
