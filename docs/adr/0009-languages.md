# 0009. Three languages from the start: Russian, English, Georgian

Status: Accepted · Date: 2026-10-21 · Spec: §11; kickoff hard rules; the owner, 2026-10-21

## Context

The kickoff made Russian the only MVP language but required every string to live in
a dictionary from the first commit. On 2026-10-21 the owner asked for a language
switch with at least Russian, English and Georgian, and for an interface that people
can follow without reading the chosen language.

## Decision

- **Locales `ru`, `en` and `ka`, from phase 0.** Every user-facing string, in the UI
  and in the bot, is a key in one dictionary per locale. Nothing user-facing comes
  from server text: the api returns machine codes (ADR-0007), and the UI maps them to
  keys.
- **Frontend.** `frontend/src/i18n/ru.ts` is the source, with flat keys
  (`home.hello`). `en.ts` and `ka.ts` are typed `Record<MessageKey, string>`, so a
  missing or extra key fails `tsc`. Placeholders look like `{name}`.
  `Intl.PluralRules` arrives with the first count (phase 1). All three dictionaries
  are bundled; at a few hundred strings they cost a few KB gzip (ADR-0003).
- **Backend.** The bot's strings live in `swap/i18n.py`, one dict per locale. A test
  checks that all three have the same keys and the same placeholders.
- **Which language.** The user's choice (`users.locale`) if they made one. Otherwise
  Telegram's `language_code`: `ru`, `ka` and `en` map to themselves, and anything else
  falls back to English. The choice is stored on the server (`PATCH /api/v1/me`), so
  the bot writes in the app's language.
- **The switch** sits behind a globe icon and lists each language in its own script:
  Русский, English, ქართული. Someone who can't read the current UI still finds their
  own language's name. Until the profile screen exists, it lives on Home.
- **Formats** come from `Intl`, with `ru-RU`, `en-GB` and `ka-GE`. Amounts, dates and
  plurals are never formatted by hand.
- **The bot's profile texts** (description, short description, the /start command)
  are set per language through the Bot API when the worker starts (ADR-0008). Every
  other language gets the English default.
- **Translations.** I write all three, and a PR that adds a string adds it in all
  three. The Georgian needs a native speaker's read before MVP acceptance.

## Consequences

- Every string costs three translations, and the compiler refuses a missing one.
- Georgian runs longer than Russian, and Russian longer than English, so layouts wrap:
  no fixed-width buttons, and no text inside icons.
- Georgian script needs no web font. iOS, Android, macOS and Windows all ship one, and
  the font stack falls back to the system's.

## Alternatives considered

- **i18next or react-intl.** ICU messages and lazy loading, for 15–40 KB gzip, solve
  problems that three bundled dictionaries don't have.
- **Russian only until v1** (the kickoff's default). Overridden by the owner.
- **Flags for languages.** A flag names a country, not a language: Russian isn't only
  Russia's, and English isn't one country's.
