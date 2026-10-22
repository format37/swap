"""Other people as the api shows them: their name, @username and photo, nothing more (§7)."""

import uuid
from typing import Self

from pydantic import BaseModel

from swap.models import User


class Person(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str | None
    username: str | None
    # Telegram's link to their photo, which the app loads from Telegram (ADR-0027).
    photo_url: str | None

    @classmethod
    def of(cls, user: User) -> Self:
        return cls(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            photo_url=user.photo_url,
        )
