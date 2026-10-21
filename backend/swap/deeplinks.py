"""The bot's t.me links: invites (`?start=`) and the cards «Открыть» opens (`?startapp=`).

ADR-0012 and ADR-0013. Telegram allows `A-Za-z0-9_-` in both parameters, 64
characters in `start` and 512 in `startapp`.
"""

import uuid
from typing import Literal

INVITE_PREFIX = "inv_"

type TargetKind = Literal["link", "order", "deal"]


def invite_url(bot_username: str, token: str) -> str:
    return f"https://t.me/{bot_username}?start={INVITE_PREFIX}{token}"


def target(kind: TargetKind, id_: uuid.UUID) -> str:
    """What the app opens: `deal_<uuid>` opens that deal's card."""
    return f"{kind}_{id_}"


def startapp_url(bot_username: str, target: str) -> str:
    """The Main Mini App, opened on `target` (ADR-0013)."""
    return f"https://t.me/{bot_username}?startapp={target}"
