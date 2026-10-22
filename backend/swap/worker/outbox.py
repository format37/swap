"""The Telegram outbox: every few seconds, send what is due (ADR-0014).

Each message is claimed, sent and settled in a short transaction of its own, so a
crash loses nothing: the next sweep finds what is still pending. If the worker dies
between Telegram's answer and the commit, the message goes out twice (ADR-0005).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from sqlalchemy import func, select

from swap.bot.handlers import open_card_keyboard
from swap.config import Settings
from swap.db import Sessionmaker
from swap.i18n import format_amount, resolve_locale, t
from swap.logs import Redactor
from swap.models import Notification, NotificationStatus, User
from swap.notifications import KIND_OF

log = structlog.get_logger("swap.outbox")

# One sweep sends at most this many, so a backlog drains over a few sweeps.
BATCH = 20
MAX_ATTEMPTS = 8
BACKOFF_BASE = timedelta(seconds=30)
BACKOFF_MAX = timedelta(hours=1)


def backoff(attempts: int) -> timedelta:
    """How long to wait after the `attempts`-th failure: 1 min, 2, 4, … an hour at most."""
    return min(BACKOFF_BASE * (1 << attempts), BACKOFF_MAX)


async def send_due(sessionmaker: Sessionmaker, bot: Bot, settings: Settings) -> int:
    """Send what is due, oldest first. Returns how many went out."""
    redactor = Redactor(settings.secrets())
    sent = 0
    for _ in range(BATCH):
        async with sessionmaker() as db:
            note = await db.scalar(
                select(Notification)
                .where(
                    Notification.tg_status == NotificationStatus.PENDING,
                    Notification.next_attempt_at <= func.now(),
                )
                .order_by(Notification.next_attempt_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if note is None:
                break
            recipient = await db.get(User, note.recipient_id)
            if recipient is None:  # pragma: no cover - the foreign key guarantees the row
                break
            go_on = await _send(note, recipient, bot, settings, redactor)
            await db.commit()
        if note.tg_status == NotificationStatus.SENT:
            sent += 1
        if not go_on:
            break
    return sent


async def _send(
    note: Notification, recipient: User, bot: Bot, settings: Settings, redactor: Redactor
) -> bool:
    """Try one message and record what happened. False means Telegram asked us to slow down."""
    if not recipient.can_message or recipient.telegram_id is None:
        note.tg_status = NotificationStatus.SKIPPED
        return True
    # What the recipient switched off in the settings goes unsent (QUESTIONS K1).
    if recipient.notifications_off or KIND_OF.get(note.type) in recipient.muted_kinds:
        note.tg_status = NotificationStatus.SKIPPED
        note.last_error = "switched off"
        return True
    locale = resolve_locale(recipient.locale, recipient.language_code)
    try:
        values = {
            key: format_amount(Decimal(value), locale) if "amount" in key else value
            for key, value in note.params.items()
        }
        text = t(locale, note.type, **values)
        keyboard = (
            open_card_keyboard(locale, settings.telegram_bot_username, note.target)
            if note.target
            else None
        )
        message = await bot.send_message(recipient.telegram_id, text, reply_markup=keyboard)
    except TelegramRetryAfter as exc:
        # Flood control: this one waits, and so does the rest of the sweep.
        note.next_attempt_at = datetime.now(UTC) + timedelta(seconds=exc.retry_after)
        log.warning("outbox slowed down by Telegram", retry_after=exc.retry_after)
        return False
    except TelegramForbiddenError:
        # They blocked the bot. The message stays in the in-app feed (slice 5).
        recipient.can_message = False
        note.tg_status = NotificationStatus.SKIPPED
        log.info("recipient blocked the bot", type=note.type)
    except (TelegramBadRequest, KeyError, ValueError, ArithmeticError) as exc:
        # Retrying won't change a refusal, or a message we can't word.
        note.tg_status = NotificationStatus.FAILED
        note.last_error = _describe(exc, redactor)
        log.error("notification refused", type=note.type, error=note.last_error)
    except Exception as exc:
        # Anything else may pass: the network, the Bot API server restarting.
        note.attempts += 1
        note.last_error = _describe(exc, redactor)
        if note.attempts >= MAX_ATTEMPTS:
            note.tg_status = NotificationStatus.FAILED
            log.error("notification gave up", type=note.type, error=note.last_error)
        else:
            note.next_attempt_at = datetime.now(UTC) + backoff(note.attempts)
            log.warning("notification will retry", type=note.type, error=note.last_error)
    else:
        note.tg_status = NotificationStatus.SENT
        note.tg_message_id = message.message_id
    return True


def _describe(exc: Exception, redactor: Redactor) -> str:
    # A network error can quote a Bot API URL, and that URL holds the token.
    detail = exc.message if isinstance(exc, TelegramAPIError) else str(exc)
    return redactor.scrub(f"{type(exc).__name__}: {detail}")[:300]
