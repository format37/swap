"""The bot's client, and its profile in every language (ADR-0008, ADR-0009)."""

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

from swap.config import Settings
from swap.i18n import DEFAULT_LOCALE, LOCALES, Locale, t


def make_bot(settings: Settings, api_base: str) -> Bot:
    """A client of the VPS's own Bot API server, never of the cloud one."""
    session = AiohttpSession(api=TelegramAPIServer.from_base(api_base, is_local=True))
    return Bot(settings.telegram_bot_token.get_secret_value(), session=session)


async def configure_bot(bot: Bot, webapp_url: str) -> None:
    """Commands, descriptions and the menu button. Every call is idempotent.

    No language code is the default, which every other language sees, so it is English.
    """
    targets: list[tuple[str | None, Locale]] = [(None, DEFAULT_LOCALE)]
    targets += [(locale, locale) for locale in LOCALES if locale != DEFAULT_LOCALE]
    for language_code, locale in targets:
        await bot.set_my_commands(
            [BotCommand(command="start", description=t(locale, "bot.command.start"))],
            language_code=language_code,
        )
        await bot.set_my_description(t(locale, "bot.description"), language_code=language_code)
        await bot.set_my_short_description(
            t(locale, "bot.short_description"), language_code=language_code
        )
    # The brand name is the same in every language, and the button has only one text.
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Swap", web_app=WebAppInfo(url=webapp_url))
    )
