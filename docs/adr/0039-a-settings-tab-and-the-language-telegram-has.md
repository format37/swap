# 0039. A settings tab, and the language Telegram has

Status: Accepted · Date: 2026-10-22 · Spec: §7 «Локализация», §11; QUESTIONS L5, L6; amends ADR-0009 and Q-B14

## Context

**The settings.** The profile screen holds the settings: notifications, the language,
the privacy page, the CSV export, and deleting the history or the account (K1–K4, K6,
K9). It opens from the avatar in Home's header (Q-B14). The owner looked for a settings
button and found none (L5): nothing marks the avatar as one.

The tab bar has «Главная» and «Связи». Q-B14 planned «Сделки» and «Балансы» as well.
Running deals live in Home's lists instead, and balances (Q-B2) wait in
«Потенциальные планы».

**The language.** The app speaks the language the user chose in it (`users.locale`), and
only without a choice the language of their Telegram (`language_code`) (ADR-0009).
Nothing takes a choice back. The owner had chosen Russian in the app, and his Telegram is
in English. He expected Swap to follow Telegram, or to have a setting (L6).

## Decision

**A third tab.** «Настройки», with a gear, opens the profile screen, beside «Главная» and
«Связи». Home's avatar still opens it too.

**«Как в Telegram».**
- The language screen lists «Как в Telegram» first, with the language it gives now, and
  then Русский, English and ქართული.
- Choosing it clears the choice: `PATCH /me` with `"locale": null`. Leaving the field
  out still changes nothing.
- The app and the bot then follow Telegram's `language_code` again, which every sign-in
  refreshes.
- A new account starts there, as it always has.
- The settings row «Язык» says «Как в Telegram» or the chosen language.

## Consequences

- Telegram's language is the language of the Telegram app, not of the phone.
- Whoever wants Swap in another language than their Telegram's still chooses it, as
  anyone with Georgian Swap and Russian Telegram does.
- Once a choice is cleared, the bot writes in Telegram's language as of the user's last
  sign-in.

## Alternatives considered

- **Always following Telegram.** Then Swap couldn't differ from Telegram, and a Georgian
  speaker with Russian Telegram couldn't have Georgian Swap.
- **Dropping the choice whenever Telegram's language changes.** A choice would then vanish
  without the user asking for it.
- **A gear in Home's header, beside the avatar.** A tab can be seen from every main
  screen, and it says what it is.
