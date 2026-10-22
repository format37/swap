"""Signing in: initData from this launch in, a bearer token for this launch out (ADR-0011)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel, Field

from swap.api.deps import AppSettings, Db
from swap.api.errors import ApiError, Problem
from swap.api.v1.me import Me
from swap.init_data import InitDataError, validate_init_data
from swap.models import AuthSession
from swap.sessions import hash_token, new_token
from swap.users import upsert_user

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramSignIn(BaseModel):
    # Telegram's initData is a few hundred bytes; the cap keeps junk cheap to refuse.
    init_data: str = Field(min_length=1, max_length=8192)


class SignedIn(BaseModel):
    token: str
    expires_at: datetime
    me: Me


@router.post("/telegram", responses={401: {"model": Problem}, 422: {"model": Problem}})
async def sign_in_with_telegram(body: TelegramSignIn, db: Db, settings: AppSettings) -> SignedIn:
    try:
        launch = validate_init_data(
            body.init_data,
            settings.telegram_bot_token.get_secret_value(),
            max_age=timedelta(seconds=settings.init_data_max_age_s),
        )
    except InitDataError as exc:
        raise ApiError(401, exc.code) from exc

    user = await upsert_user(db, launch.user, can_message=launch.user.allows_write_to_pm)
    # A launch that brings no link keeps the stored one: not every launch is known to carry
    # it, and a hidden photo comes as Telegram's letter picture, a link of its own
    # (QUESTIONS L3, ADR-0027).
    if launch.user.photo_url:
        user.photo_url = launch.user.photo_url
    token = new_token()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.session_ttl_s)
    db.add(AuthSession(user_id=user.id, token_hash=hash_token(token), expires_at=expires_at))
    await db.commit()
    return SignedIn(token=token, expires_at=expires_at, me=Me.of(user))
