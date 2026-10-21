"""What the bot answers: /start, with or without an invite, and a pointer to the app."""

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy import select

from swap.config import Settings
from swap.db import Sessionmaker
from swap.deeplinks import INVITE_PREFIX, startapp_url, target
from swap.i18n import Locale, resolve_locale, t
from swap.links import Opened, OpenedInvite, open_invite
from swap.models import User
from swap.users import person_label, upsert_user


def open_app_keyboard(locale: Locale, webapp_url: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text=t(locale, "button.open"), web_app=WebAppInfo(url=webapp_url))
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def open_card_keyboard(locale: Locale, bot_username: str, card: str) -> InlineKeyboardMarkup:
    """«Открыть» on one card: the Main Mini App, opened at `card` (ADR-0013)."""
    button = InlineKeyboardButton(
        text=t(locale, "button.open_card"), url=startapp_url(bot_username, card)
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def invite_reply(
    opened: OpenedInvite, locale: Locale, settings: Settings
) -> tuple[str, InlineKeyboardMarkup]:
    """What the bot says when someone presses /start with an invite (ADR-0012)."""
    if opened.inviter is None or opened.link is None:
        key = "invite.own" if opened.outcome is Opened.OWN else "invite.invalid"
        return t(locale, key), open_app_keyboard(locale, settings.webapp_url)
    text = t(locale, f"invite.{opened.outcome.value}", name=person_label(opened.inviter))
    card = target("link", opened.link.id)
    return text, open_card_keyboard(locale, settings.telegram_bot_username, card)


def build_router() -> Router:
    """A fresh router per dispatcher: aiogram refuses to attach one router twice."""
    router = Router(name="swap")
    # Groups are off in BotFather; this keeps a stray group update from being answered.
    router.message.filter(F.chat.type == ChatType.PRIVATE)

    @router.message(CommandStart())
    async def start(
        message: Message, command: CommandObject, sessionmaker: Sessionmaker, settings: Settings
    ) -> None:
        if message.from_user is None:
            return
        payload = command.args or ""
        opened: OpenedInvite | None = None
        async with sessionmaker() as db:
            # Pressing /start is what allows the bot to write to someone (Q-B12).
            user = await upsert_user(db, message.from_user, can_message=True)
            if payload.startswith(INVITE_PREFIX):
                opened = await open_invite(db, user, payload.removeprefix(INVITE_PREFIX))
            await db.commit()
        locale = resolve_locale(user.locale, user.language_code)
        if opened is not None:
            text, keyboard = invite_reply(opened, locale, settings)
            await message.answer(text, reply_markup=keyboard)
            return
        await message.answer(
            t(locale, "start.greeting", name=user.first_name),
            reply_markup=open_app_keyboard(locale, settings.webapp_url),
        )

    @router.message()
    async def anything_else(
        message: Message, sessionmaker: Sessionmaker, settings: Settings
    ) -> None:
        if message.from_user is None:
            return
        async with sessionmaker() as db:
            chosen = await db.scalar(
                select(User.locale).where(User.telegram_id == message.from_user.id)
            )
        locale = resolve_locale(chosen, message.from_user.language_code)
        await message.answer(
            t(locale, "start.hint"), reply_markup=open_app_keyboard(locale, settings.webapp_url)
        )

    return router
