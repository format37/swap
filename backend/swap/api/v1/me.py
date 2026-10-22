"""The signed-in user: who they are, their language (ADR-0009) and time zone (Q-B17)."""

import uuid
import zoneinfo
from typing import Self

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from swap.api.deps import CurrentUser, Db
from swap.api.errors import Problem
from swap.i18n import Locale, resolve_locale
from swap.models import User

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
        )


class MeUpdate(BaseModel):
    """Only what is sent changes."""

    locale: Locale | None = None
    # An IANA zone, such as Asia/Tbilisi.
    tz: str | None = None

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
    await db.commit()
    return Me.of(user)
