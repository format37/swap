"""What the bot answers. In phase 0 that is /start and a pointer to the app."""

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy import select

from swap.config import Settings
from swap.db import Sessionmaker
from swap.i18n import Locale, resolve_locale, t
from swap.models import User
from swap.users import upsert_user


def open_app_keyboard(locale: Locale, webapp_url: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text=t(locale, "button.open"), web_app=WebAppInfo(url=webapp_url))
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def build_router() -> Router:
    """A fresh router per dispatcher: aiogram refuses to attach one router twice."""
    router = Router(name="swap")
    # Groups are off in BotFather; this keeps a stray group update from being answered.
    router.message.filter(F.chat.type == ChatType.PRIVATE)

    @router.message(CommandStart())
    async def start(message: Message, sessionmaker: Sessionmaker, settings: Settings) -> None:
        if message.from_user is None:
            return
        async with sessionmaker() as db:
            # Pressing /start is what allows the bot to write to someone (Q-B12).
            user = await upsert_user(db, message.from_user, can_message=True)
            await db.commit()
        locale = resolve_locale(user.locale, user.language_code)
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
