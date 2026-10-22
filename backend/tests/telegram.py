"""A stand-in for the Bot API server, shared by the worker's tests."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendDocument, SendMessage, TelegramMethod
from aiogram.types import Chat, Message


class RecordingSession(BaseSession):
    """Records every call and answers as Telegram would, or refuses as `failures` say."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        # Each SendMessage takes the next one, if any, and raises what it returns.
        self.failures: list[Callable[[TelegramMethod[Any]], Exception]] = []

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,  # noqa: ASYNC109 - aiogram's BaseSession signature
    ) -> Any:
        self.calls.append(method)
        if isinstance(method, SendDocument):
            return Message(
                message_id=len(self.calls),
                date=datetime.now(UTC),
                chat=Chat(id=int(method.chat_id), type="private"),
                caption=method.caption,
            )
        if isinstance(method, SendMessage):
            if self.failures:
                raise self.failures.pop(0)(method)
            return Message(
                message_id=len(self.calls),
                date=datetime.now(UTC),
                chat=Chat(id=int(method.chat_id), type="private"),
                text=method.text,
            )
        return True

    async def stream_content(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    async def close(self) -> None:
        return None
