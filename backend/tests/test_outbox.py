"""The Telegram outbox (ADR-0014): written with its change, worded and sent by the worker."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.methods import SendMessage
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swap.config import Settings
from swap.i18n import t
from swap.models import Notification, NotificationStatus, User
from swap.notifications import notify
from swap.users import upsert_user
from swap.worker.outbox import BACKOFF_MAX, MAX_ATTEMPTS, backoff, send_due
from tests.conftest import TEST_BOT_TOKEN
from tests.telegram import RecordingSession

Sessions = async_sessionmaker[AsyncSession]
CARD = "link_6f1c9a52-0d7e-4d53-9d0c-8f6f3e2b7c11"


@pytest.fixture
def telegram() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
def bot(telegram: RecordingSession) -> Bot:
    return Bot(TEST_BOT_TOKEN, session=telegram)


async def person(sessions: Sessions, telegram_id: int = 2001, *, can_message: bool = True) -> User:
    profile = SimpleNamespace(
        id=telegram_id, first_name="Nino", last_name=None, username=None, language_code="ru"
    )
    async with sessions() as db:
        user = await upsert_user(db, profile, can_message=can_message)
        await db.commit()
    return user


async def queue(sessions: Sessions, recipient: User, count: int = 1) -> None:
    async with sessions() as db:
        for _ in range(count):
            notify(db, recipient.id, "link.requested", target=CARD, name="Alex (@format37)")
        await db.commit()


async def notes(sessions: Sessions) -> list[Notification]:
    async with sessions() as db:
        found = await db.scalars(select(Notification).order_by(Notification.created_at))
        return list(found)


# --- written with the change -------------------------------------------------------


async def test_a_message_is_queued_only_if_its_change_commits(sessionmaker: Sessions) -> None:
    nino = await person(sessionmaker)
    async with sessionmaker() as db:
        notify(db, nino.id, "link.requested", target=CARD, name="Alex")
        await db.rollback()
    assert await notes(sessionmaker) == []


# --- sending -------------------------------------------------------------------------


async def test_a_due_message_goes_out_in_the_recipients_language_with_open(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker)
    await queue(sessionmaker, nino)
    assert await send_due(sessionmaker, bot, settings) == 1

    [sent] = telegram.calls
    assert isinstance(sent, SendMessage)
    assert sent.chat_id == 2001
    assert sent.text == t("ru", "link.requested", name="Alex (@format37)")
    [[button]] = sent.reply_markup.inline_keyboard  # type: ignore[union-attr]
    assert button.url == f"https://t.me/peertopeerswapbot?startapp={CARD}"
    [note] = await notes(sessionmaker)
    assert note.tg_status == NotificationStatus.SENT
    assert note.tg_message_id == 1
    assert await send_due(sessionmaker, bot, settings) == 0  # nothing twice


async def test_the_words_are_those_of_the_language_at_sending_time(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker)
    await queue(sessionmaker, nino)
    async with sessionmaker() as db:
        await db.execute(update(User).values(locale="ka"))
        await db.commit()
    await send_due(sessionmaker, bot, settings)
    [sent] = telegram.calls
    assert isinstance(sent, SendMessage)
    assert sent.text == t("ka", "link.requested", name="Alex (@format37)")


async def test_a_message_not_yet_due_waits(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker)
    await queue(sessionmaker, nino)
    async with sessionmaker() as db:
        await db.execute(
            update(Notification).values(next_attempt_at=datetime.now(UTC) + timedelta(minutes=1))
        )
        await db.commit()
    assert await send_due(sessionmaker, bot, settings) == 0
    assert telegram.calls == []


async def test_someone_the_bot_may_not_write_to_is_skipped_without_a_call(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker, can_message=False)
    await queue(sessionmaker, nino)
    await send_due(sessionmaker, bot, settings)
    assert telegram.calls == []
    [note] = await notes(sessionmaker)
    assert note.tg_status == NotificationStatus.SKIPPED


# --- refusals and failures -----------------------------------------------------------


async def test_a_blocked_bot_stops_messages_to_that_person(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker)
    await queue(sessionmaker, nino, count=2)
    telegram.failures.append(
        lambda method: TelegramForbiddenError(method, "Forbidden: bot was blocked by the user")
    )
    await send_due(sessionmaker, bot, settings)
    # The first send learned the block, so the second isn't even tried.
    assert len(telegram.calls) == 1
    assert [note.tg_status for note in await notes(sessionmaker)] == ["skipped", "skipped"]
    async with sessionmaker() as db:
        assert await db.scalar(select(User.can_message).where(User.id == nino.id)) is False


async def test_flood_control_waits_and_ends_the_sweep(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker)
    await queue(sessionmaker, nino, count=2)
    telegram.failures.append(
        lambda method: TelegramRetryAfter(method, "Too Many Requests", retry_after=30)
    )
    before = datetime.now(UTC)
    await send_due(sessionmaker, bot, settings)
    assert len(telegram.calls) == 1
    both = await notes(sessionmaker)
    assert [note.tg_status for note in both] == ["pending", "pending"]
    assert [note.attempts for note in both] == [0, 0]  # flood control is no failure
    waiting = [note for note in both if note.next_attempt_at >= before + timedelta(seconds=30)]
    assert len(waiting) == 1


async def test_a_refusal_fails_for_good(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker)
    await queue(sessionmaker, nino)
    telegram.failures.append(
        lambda method: TelegramBadRequest(method, "Bad Request: chat not found")
    )
    await send_due(sessionmaker, bot, settings)
    [note] = await notes(sessionmaker)
    assert note.tg_status == NotificationStatus.FAILED
    assert note.last_error == "TelegramBadRequest: Bad Request: chat not found"


async def test_other_failures_back_off_and_finally_give_up(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker)
    await queue(sessionmaker, nino)
    url = f"http://127.0.0.1:8081/bot{TEST_BOT_TOKEN}/sendMessage"
    telegram.failures.append(lambda method: TelegramNetworkError(method, f"timeout on {url}"))
    before = datetime.now(UTC)
    await send_due(sessionmaker, bot, settings)
    [note] = await notes(sessionmaker)
    assert note.tg_status == NotificationStatus.PENDING
    assert note.attempts == 1
    assert note.next_attempt_at >= before + backoff(1)
    # The error is kept for whoever reads the table, without the token.
    assert note.last_error is not None
    assert TEST_BOT_TOKEN not in note.last_error
    assert "[redacted]" in note.last_error

    async with sessionmaker() as db:
        # Due again. The test runs in one transaction, whose now() is its start.
        await db.execute(
            update(Notification).values(
                attempts=MAX_ATTEMPTS - 1, next_attempt_at=datetime.now(UTC) - timedelta(hours=1)
            )
        )
        await db.commit()
    telegram.failures.append(lambda method: TelegramNetworkError(method, "timeout"))
    await send_due(sessionmaker, bot, settings)
    [note] = await notes(sessionmaker)
    assert note.tg_status == NotificationStatus.FAILED
    assert note.attempts == MAX_ATTEMPTS


def test_backoff_doubles_up_to_an_hour() -> None:
    assert [backoff(n) for n in (1, 2, 3)] == [
        timedelta(minutes=1),
        timedelta(minutes=2),
        timedelta(minutes=4),
    ]
    assert backoff(MAX_ATTEMPTS) == BACKOFF_MAX == timedelta(hours=1)


async def test_one_sweep_sends_a_batch_and_leaves_the_rest(
    sessionmaker: Sessions, bot: Bot, telegram: RecordingSession, settings: Settings
) -> None:
    nino = await person(sessionmaker)
    await queue(sessionmaker, nino, count=25)
    assert await send_due(sessionmaker, bot, settings) == 20
    assert await send_due(sessionmaker, bot, settings) == 5
    async with sessionmaker() as db:
        pending = await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.tg_status == NotificationStatus.PENDING)
        )
    assert pending == 0
