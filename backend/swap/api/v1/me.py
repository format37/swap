"""The signed-in user: who they are, their language (ADR-0009) and time zone (Q-B17)."""

import uuid
import zoneinfo
from datetime import UTC, datetime, timedelta
from typing import Self

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import exists, func, select

from swap import accounts
from swap.api.deps import CurrentUser, Db
from swap.api.errors import Problem
from swap.errors import DomainError
from swap.i18n import Locale, resolve_locale
from swap.models import Notification, NotificationKind, User
from swap.notifications import notify

router = APIRouter(tags=["me"], responses={401: {"model": Problem}})

# The agreement's version (Q-B15, QUESTIONS K3). A new text bumps it, and everyone accepts
# it again at their next launch.
TERMS_VERSION = 1


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
    # What «Как в Telegram» gives: their Telegram's language (ADR-0039).
    telegram_locale: Locale
    # Null until the app sends the device's zone at the first launch.
    tz: str | None
    # What they switched off: everything, or kinds of messages (QUESTIONS K1).
    notifications_off: bool
    muted_kinds: list[NotificationKind]
    # Whether they accepted the agreement as it stands; until then the app shows it.
    terms_accepted: bool

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
            telegram_locale=resolve_locale(None, user.language_code),
            tz=user.tz,
            notifications_off=user.notifications_off,
            muted_kinds=[NotificationKind(kind) for kind in user.muted_kinds],
            terms_accepted=(user.terms_version or 0) >= TERMS_VERSION,
        )


class MeUpdate(BaseModel):
    """Only what is sent changes."""

    # A language, or null to let the choice go and follow Telegram's (ADR-0039).
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
    if "locale" in body.model_fields_set:
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


@router.post("/me/terms")
async def accept_terms(user: CurrentUser, db: Db) -> Me:
    """«Принимаю»: the agreement as it stands now (Q-B15, QUESTIONS K3)."""
    user.terms_version = TERMS_VERSION
    user.terms_accepted_at = datetime.now(UTC)
    await db.commit()
    return Me.of(user)


# One export at a time is plenty; a second tap within this sends nothing more.
EXPORT_PAUSE_S = 60


@router.post(
    "/me/export", status_code=202, responses={409: {"model": Problem}, 429: {"model": Problem}}
)
async def export_deals(user: CurrentUser, db: Db) -> Response:
    """Every deal you took part in, as a CSV file the bot sends to your chat (QUESTIONS K4)."""
    if not user.can_message:
        # The bot may not write to them until they press /start (Q-B12).
        raise DomainError(409, "export.no_chat")
    recent = await db.scalar(
        select(
            exists().where(
                Notification.recipient_id == user.id,
                Notification.type == "export.deals",
                Notification.created_at > func.now() - timedelta(seconds=EXPORT_PAUSE_S),
            )
        )
    )
    if recent:
        raise DomainError(429, "export.too_soon")
    notify(db, user.id, "export.deals")
    await db.commit()
    return Response(status_code=202)
