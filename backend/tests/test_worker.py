"""The worker: the relay's endpoint, /start, the bot's profile, and the heartbeat."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    SendMessage,
    SetChatMenuButton,
    SetMyCommands,
    SetMyDescription,
    SetMyShortDescription,
    TelegramMethod,
)
from aiogram.types import Chat, Message
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.applications import Starlette

from swap.bot.setup import configure_bot
from swap.config import Settings
from swap.i18n import t
from swap.links import create_invite
from swap.models import Link, LinkStatus, ServiceHeartbeat, User
from swap.users import upsert_user
from swap.worker.app import create_app
from swap.worker.jobs import beat
from tests.conftest import TEST_BOT_TOKEN

Sessions = async_sessionmaker[AsyncSession]
RELAY = {"Authorization": f"Bearer {TEST_BOT_TOKEN}"}


class RecordingSession(BaseSession):
    """Stands in for the Bot API server: records every call and answers as Telegram would."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,  # noqa: ASYNC109 - aiogram's BaseSession signature
    ) -> Any:
        self.calls.append(method)
        if isinstance(method, SendMessage):
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


@pytest.fixture
def telegram() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
async def worker(
    settings: Settings, sessionmaker: Sessions, telegram: RecordingSession
) -> AsyncIterator[tuple[AsyncClient, Starlette]]:
    app = create_app(settings, sessionmaker=sessionmaker, bot=Bot(TEST_BOT_TOKEN, session=telegram))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://worker") as client:
        yield client, app


def message(text: str, *, user_id: int = 2001, language_code: str | None = "ru") -> dict[str, Any]:
    """A private message the way the relay forwards it: the raw Message object."""
    body: dict[str, Any] = {
        "message_id": 7,
        "date": 1761048000,
        "chat": {"id": user_id, "type": "private", "first_name": "Nino"},
        "from": {
            "id": user_id,
            "is_bot": False,
            "first_name": "Nino",
            "username": "nino",
            "language_code": language_code,
        },
        "text": text,
    }
    if text.startswith("/"):
        body["entities"] = [
            {"type": "bot_command", "offset": 0, "length": len(text.split(maxsplit=1)[0])}
        ]
    return body


async def settle(app: Starlette) -> None:
    """Wait for the updates that the endpoint handed to the background."""
    while app.state.pending:
        await asyncio.gather(*list(app.state.pending))


# --- refused ---------------------------------------------------------------------


async def test_the_relay_must_present_the_bot_token(
    worker: tuple[AsyncClient, Starlette], telegram: RecordingSession
) -> None:
    client, app = worker
    for headers in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": TEST_BOT_TOKEN}):
        response = await client.post("/message", json=message("/start"), headers=headers)
        assert response.status_code == 401
    await settle(app)
    assert telegram.calls == []


async def test_without_telegram_the_endpoint_is_off(
    settings: Settings, sessionmaker: Sessions
) -> None:
    # No TELEGRAM_API_BASE, so no bot: how the worker runs locally and in CI.
    app = create_app(settings, sessionmaker=sessionmaker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://worker") as client:
        assert (await client.get("/healthz")).json() == {"status": "ok", "telegram": False}
        response = await client.post("/message", json=message("/start"), headers=RELAY)
    assert response.status_code == 503


async def test_a_body_that_is_neither_is_ignored(
    worker: tuple[AsyncClient, Starlette], telegram: RecordingSession
) -> None:
    client, app = worker
    response = await client.post("/message", json={"poll": {}}, headers=RELAY)
    assert response.json() == {"type": "empty"}
    await settle(app)
    assert telegram.calls == []


# --- handled ---------------------------------------------------------------------


async def test_start_greets_in_the_users_language_with_the_app_button(
    worker: tuple[AsyncClient, Starlette],
    telegram: RecordingSession,
    sessionmaker: Sessions,
    settings: Settings,
) -> None:
    client, app = worker
    response = await client.post("/message", json=message("/start"), headers=RELAY)
    # Anything but "empty" and the relay would try to send a reply of its own.
    assert response.json() == {"type": "empty"}
    await settle(app)

    [sent] = telegram.calls
    assert isinstance(sent, SendMessage)
    assert sent.chat_id == 2001
    assert sent.text.startswith("Привет, Nino!")
    [[button]] = sent.reply_markup.inline_keyboard  # type: ignore[union-attr]
    assert button.text == "Открыть Swap"
    assert button.web_app is not None
    assert button.web_app.url == settings.webapp_url

    async with sessionmaker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == 2001))
    assert user is not None
    assert user.can_message is True


async def test_any_other_message_points_to_the_app(
    worker: tuple[AsyncClient, Starlette], telegram: RecordingSession
) -> None:
    client, app = worker
    await client.post("/message", json=message("hello?", language_code="ka"), headers=RELAY)
    await settle(app)
    [sent] = telegram.calls
    assert isinstance(sent, SendMessage)
    assert sent.text == "ყველაფერი აპლიკაციაში ხდება. გახსენით ის ქვემოთ მოცემული ღილაკით."


async def test_the_language_picked_in_the_app_beats_telegrams(
    worker: tuple[AsyncClient, Starlette], telegram: RecordingSession, sessionmaker: Sessions
) -> None:
    client, app = worker
    await client.post("/message", json=message("/start"), headers=RELAY)
    await settle(app)
    async with sessionmaker() as db:
        await db.execute(update(User).values(locale="en"))
        await db.commit()
    telegram.calls.clear()

    await client.post("/message", json=message("/start", language_code="ru"), headers=RELAY)
    await settle(app)
    [sent] = telegram.calls
    assert isinstance(sent, SendMessage)
    assert sent.text.startswith("Hi, Nino!")


async def invite_from(sessions: Sessions, telegram_id: int, first_name: str) -> str:
    """An invite's token, made by someone who has pressed /start before."""
    profile = SimpleNamespace(
        id=telegram_id,
        first_name=first_name,
        last_name=None,
        username=first_name.lower(),
        language_code="ru",
    )
    async with sessions() as db:
        inviter = await upsert_user(db, profile, can_message=True)
        _, token = await create_invite(db, inviter.id, timedelta(hours=72))
        await db.commit()
    return token


async def test_an_invite_names_the_inviter_and_opens_the_request(
    worker: tuple[AsyncClient, Starlette], telegram: RecordingSession, sessionmaker: Sessions
) -> None:
    client, app = worker
    token = await invite_from(sessionmaker, 1001, "Alex")
    await client.post("/message", json=message(f"/start inv_{token}"), headers=RELAY)
    await settle(app)

    [sent] = telegram.calls
    assert isinstance(sent, SendMessage)
    assert sent.chat_id == 2001
    assert sent.text.startswith("Alex (@alex) приглашает вас в Swap.")
    async with sessionmaker() as db:
        link = await db.scalar(select(Link))
        nino = await db.scalar(select(User).where(User.telegram_id == 2001))
    assert link is not None
    assert link.status == LinkStatus.PENDING
    assert nino is not None
    assert nino.can_message is True
    # «Открыть» opens the Main Mini App on the request itself (ADR-0013).
    [[button]] = sent.reply_markup.inline_keyboard  # type: ignore[union-attr]
    assert button.text == "Открыть"
    assert button.url == f"https://t.me/peertopeerswapbot?startapp=link_{link.id}"


@pytest.mark.parametrize(
    ("payload", "key"),
    [("inv_not-a-token", "invite.invalid"), ("inv_", "invite.invalid"), ("own", "invite.own")],
)
async def test_an_invite_that_links_nobody_says_why(
    worker: tuple[AsyncClient, Starlette],
    telegram: RecordingSession,
    sessionmaker: Sessions,
    settings: Settings,
    payload: str,
    key: str,
) -> None:
    client, app = worker
    if payload == "own":
        payload = f"inv_{await invite_from(sessionmaker, 2001, 'Nino')}"
    await client.post("/message", json=message(f"/start {payload}"), headers=RELAY)
    await settle(app)
    [sent] = telegram.calls
    assert isinstance(sent, SendMessage)
    assert sent.text == t("ru", key)
    [[button]] = sent.reply_markup.inline_keyboard  # type: ignore[union-attr]
    assert button.web_app is not None
    assert button.web_app.url == settings.webapp_url
    async with sessionmaker() as db:
        assert await db.scalar(select(Link)) is None


async def test_another_start_payload_gets_the_greeting(
    worker: tuple[AsyncClient, Starlette], telegram: RecordingSession
) -> None:
    client, app = worker
    await client.post("/message", json=message("/start hello"), headers=RELAY)
    await settle(app)
    [sent] = telegram.calls
    assert isinstance(sent, SendMessage)
    assert sent.text.startswith("Привет, Nino!")


async def test_a_reduced_callback_query_is_accepted(
    worker: tuple[AsyncClient, Starlette], telegram: RecordingSession
) -> None:
    client, app = worker
    # What the relay builds for a button press: no chat_instance, a cut-down message.
    body = {
        "update_id": 1761048000,
        "callback_query": {
            "id": "42",
            "from": {"id": 2001, "is_bot": False, "first_name": "Nino"},
            "message": {
                "message_id": 7,
                "from": {"id": 123456789, "is_bot": True, "first_name": "swap"},
                "chat": {"id": 2001, "type": "private"},
                "date": 1761048000,
                "text": "",
            },
            "data": "noop",
        },
    }
    response = await client.post("/message", json=body, headers=RELAY)
    assert response.json() == {"type": "empty"}
    await settle(app)  # no handler yet: nothing is sent, and nothing fails
    assert telegram.calls == []


async def test_the_bot_profile_is_set_in_every_language(
    telegram: RecordingSession, settings: Settings
) -> None:
    await configure_bot(Bot(TEST_BOT_TOKEN, session=telegram), settings.webapp_url)
    calls: dict[type, list[Any]] = {}
    for call in telegram.calls:
        calls.setdefault(type(call), []).append(call)

    for method in (SetMyCommands, SetMyDescription, SetMyShortDescription):
        # No language code is the default that every other language sees.
        assert sorted(call.language_code or "" for call in calls[method]) == ["", "ka", "ru"]
    default = next(call for call in calls[SetMyDescription] if call.language_code is None)
    assert default.description.startswith("Swap helps")
    [menu] = calls[SetChatMenuButton]
    assert menu.menu_button.web_app.url == settings.webapp_url


async def test_the_heartbeat_is_one_row_that_moves(sessionmaker: Sessions) -> None:
    await beat(sessionmaker)
    await beat(sessionmaker)
    async with sessionmaker() as db:
        rows = (await db.execute(select(ServiceHeartbeat))).scalars().all()
    assert [row.name for row in rows] == ["worker"]
