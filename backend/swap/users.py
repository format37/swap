"""Users as Telegram describes them, created at first contact of either kind (Q-B11)."""

import uuid
from typing import Protocol

from sqlalchemy import func, or_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from swap.models import User


class TelegramProfile(Protocol):
    """What both initData's user and aiogram's `User` tell us about a person."""

    @property
    def id(self) -> int: ...
    @property
    def first_name(self) -> str: ...
    @property
    def last_name(self) -> str | None: ...
    @property
    def username(self) -> str | None: ...
    @property
    def language_code(self) -> str | None: ...


async def upsert_user(db: AsyncSession, profile: TelegramProfile, *, can_message: bool) -> User:
    """Create the user, or refresh their name, username and language.

    `can_message` only ever turns on here. It turns off when Telegram refuses a send
    (ADR-0005).
    """
    if profile.username:
        # Telegram has moved this username to `profile`, so whoever still holds it here
        # has changed theirs.
        await db.execute(
            update(User)
            .where(
                func.lower(User.username) == profile.username.lower(),
                User.telegram_id != profile.id,
            )
            .values(username=None)
        )
    statement = insert(User).values(
        id=uuid.uuid4(),
        telegram_id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name or None,
        username=profile.username or None,
        language_code=profile.language_code or None,
        can_message=can_message,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[User.telegram_id],
        set_={
            "first_name": statement.excluded.first_name,
            "last_name": statement.excluded.last_name,
            "username": statement.excluded.username,
            "language_code": statement.excluded.language_code,
            "can_message": or_(User.can_message, statement.excluded.can_message),
            "updated_at": func.now(),
        },
    )
    user: User | None = await db.scalar(
        statement.returning(User), execution_options={"populate_existing": True}
    )
    if user is None:  # pragma: no cover - RETURNING always yields the row
        raise RuntimeError("upsert returned no row")
    return user
