"""The signed-in user: who they are, and the language they picked (ADR-0009)."""

import uuid
from typing import Self

from fastapi import APIRouter
from pydantic import BaseModel

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
    # The language to show, already resolved; `locale_chosen` says whether the user
    # picked it or it came from Telegram.
    locale: Locale
    locale_chosen: bool

    @classmethod
    def of(cls, user: User) -> Self:
        return cls(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            locale=resolve_locale(user.locale, user.language_code),
            locale_chosen=user.locale is not None,
        )


class MeUpdate(BaseModel):
    locale: Locale


@router.get("/me")
async def get_me(user: CurrentUser) -> Me:
    return Me.of(user)


@router.patch("/me", responses={422: {"model": Problem}})
async def update_me(body: MeUpdate, user: CurrentUser, db: Db) -> Me:
    # Stored on the server so the bot writes in the same language as the app.
    user.locale = body.locale
    await db.commit()
    return Me.of(user)
