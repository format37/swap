"""The owner's relay (format37/telegram_bot) and what it POSTs to `/message` (ADR-0008).

It forwards a message as the raw Message object, and a callback query as a reduced
update without `chat_instance`. Either way it sends `Authorization: Bearer <token>`.
"""

import hmac
from typing import Any

from aiogram import Bot
from aiogram.types import Update


def relay_authorized(header: str | None, bot_token: str) -> bool:
    expected = f"Bearer {bot_token}".encode()
    return header is not None and hmac.compare_digest(header.encode(), expected)


def to_update(payload: Any, bot: Bot) -> Update | None:
    """The update the relay meant, bound to `bot` so handlers can answer. None if neither."""
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("callback_query"), dict):
        query = dict(payload["callback_query"])
        # The relay drops it, and aiogram requires it; nothing of ours reads it.
        query.setdefault("chat_instance", "")
        return Update.model_validate(
            {"update_id": 0, "callback_query": query}, context={"bot": bot}
        )
    if "message_id" in payload and "chat" in payload:
        return Update.model_validate({"update_id": 0, "message": payload}, context={"bot": bot})
    return None
