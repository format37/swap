"""Other people as the api shows them: their name, @username, photo and score, nothing more
(§7)."""

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
    # How many different people they settled a deal with (QUESTIONS J5, ADR-0029).
    score: int
    # They deleted their account: the app calls them «Удалённый участник» (QUESTIONS K2).
    deleted: bool = False

    @classmethod
    def of(cls, user: User) -> Self:
        return cls(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            photo_url=user.photo_url,
            score=user.score,
            deleted=user.deleted_at is not None,
        )
