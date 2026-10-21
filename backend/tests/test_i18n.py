import re

import pytest

from swap.i18n import LOCALES, MESSAGES, resolve_locale, t

PLACEHOLDER = re.compile(r"\{(\w+)\}")


def test_every_locale_has_every_key_with_the_same_placeholders() -> None:
    reference = MESSAGES["ru"]
    for locale in LOCALES:
        assert MESSAGES[locale].keys() == reference.keys(), locale
        for key, text in MESSAGES[locale].items():
            expected = set(PLACEHOLDER.findall(reference[key]))
            assert set(PLACEHOLDER.findall(text)) == expected, (locale, key)


def test_the_bot_profile_fits_telegrams_limits() -> None:
    for locale in LOCALES:
        assert len(t(locale, "bot.short_description")) <= 120, locale
        assert len(t(locale, "bot.description")) <= 512, locale
        assert 1 <= len(t(locale, "bot.command.start")) <= 256, locale


@pytest.mark.parametrize(
    ("chosen", "language_code", "expected"),
    [
        (None, "ru", "ru"),
        (None, "ka", "ka"),
        (None, "en", "en"),
        (None, "en-GB", "en"),
        (None, "RU", "ru"),
        (None, "pt-br", "en"),
        (None, None, "en"),
        ("ka", "ru", "ka"),
        ("xx", "ru", "ru"),
    ],
)
def test_resolve_locale(chosen: str | None, language_code: str | None, expected: str) -> None:
    assert resolve_locale(chosen, language_code) == expected
