"""The bot's strings in Russian, English and Georgian (ADR-0009).

The Mini App's strings live in `frontend/src/i18n/`. These are only the ones the bot
writes itself. The Georgian still needs a native speaker's read before MVP acceptance.
"""

from typing import Literal, get_args

type Locale = Literal["ru", "en", "ka"]
LOCALES: tuple[Locale, ...] = get_args(Locale.__value__)
# What anyone whose Telegram speaks none of the three gets.
DEFAULT_LOCALE: Locale = "en"


def resolve_locale(chosen: str | None, language_code: str | None) -> Locale:
    """The language picked in the app, else Telegram's, else English.

    Telegram sends IETF tags ("pt-br"), so only the primary subtag counts.
    """
    for candidate in (chosen, (language_code or "").split("-")[0].lower()):
        for locale in LOCALES:
            if candidate == locale:
                return locale
    return DEFAULT_LOCALE


MESSAGES: dict[Locale, dict[str, str]] = {
    "ru": {
        "start.greeting": (
            "Привет, {name}! Swap помогает договориться об обмене денег между странами "
            "с теми, кого вы знаете: вы платите их получателю у себя, они — вашему у "
            "себя. Swap не хранит и не переводит деньги: он только планирует и "
            "записывает."
        ),
        "start.hint": "Всё происходит в приложении. Откройте его кнопкой ниже.",
        "button.open": "Открыть Swap",
        "bot.command.start": "Открыть Swap",
        "bot.short_description": (
            "Обмен деньгами между странами с людьми, которых вы знаете. Swap планирует "
            "и записывает, но не хранит деньги."
        ),
        "bot.description": (
            "Swap помогает знакомым людям договориться о встречных переводах: у вас "
            "рубли в России, у знакомого — лари в Грузии, и каждый платит получателю "
            "другого у себя. Видны только те, с кем вы связаны по приглашению. Swap не "
            "хранит, не переводит и не гарантирует деньги: он ведёт сделку по шагам и "
            "показывает, кто кому должен."
        ),
    },
    "en": {
        "start.greeting": (
            "Hi, {name}! Swap helps you arrange money swaps across countries with people "
            "you know: you pay their recipient where you are, they pay yours where they "
            "are. Swap never holds or moves money; it only plans and records."
        ),
        "start.hint": "Everything happens in the app. Open it with the button below.",
        "button.open": "Open Swap",
        "bot.command.start": "Open Swap",
        "bot.short_description": (
            "Swap money across countries with people you know. Swap plans and records; "
            "it never holds money."
        ),
        "bot.description": (
            "Swap helps people who know each other arrange counter-transfers: you have "
            "roubles in Russia, a friend has lari in Georgia, and each of you pays the "
            "other's recipient at home. You only see people you have linked with by "
            "invitation. Swap never holds, moves or guarantees money: it walks the deal "
            "step by step and shows who owes whom."
        ),
    },
    "ka": {
        "start.greeting": (
            "გამარჯობა, {name}! Swap გეხმარებათ, ნაცნობებთან შეთანხმდეთ ფულის გაცვლაზე "
            "ქვეყნებს შორის: თქვენ უხდით მათ მიმღებს თქვენთან, ისინი კი თქვენსას — "
            "მათთან. Swap არ ინახავს და არ გადარიცხავს ფულს: ის მხოლოდ გეგმავს და "
            "აღრიცხავს."
        ),
        "start.hint": "ყველაფერი აპლიკაციაში ხდება. გახსენით ის ქვემოთ მოცემული ღილაკით.",
        "button.open": "Swap-ის გახსნა",
        "bot.command.start": "Swap-ის გახსნა",
        "bot.short_description": (
            "ფულის გაცვლა ქვეყნებს შორის ნაცნობებთან. Swap გეგმავს და აღრიცხავს, ფულს არ ინახავს."
        ),
        "bot.description": (
            "Swap ეხმარება ნაცნობ ადამიანებს, შეთანხმდნენ ურთიერთგადარიცხვებზე: თქვენ "
            "გაქვთ რუბლი რუსეთში, თქვენს ნაცნობს — ლარი საქართველოში, და თითოეული "
            "უხდის მეორის მიმღებს საკუთარ ქვეყანაში. ხედავთ მხოლოდ მათ, ვისთანაც "
            "მოწვევით ხართ დაკავშირებული. Swap არ ინახავს, არ გადარიცხავს და არ "
            "იძლევა ფულის გარანტიას: ის ნაბიჯ-ნაბიჯ მიჰყვება გარიგებას და აჩვენებს, "
            "ვინ ვის რა მართებს."
        ),
    },
}


def t(locale: Locale, key: str, **values: str) -> str:
    """The string for `key` in `locale`, with `{placeholders}` filled in."""
    return MESSAGES[locale][key].format(**values)
