# 0015. Georgian numbers and dates borrow Russian's rules, and Georgian dates stay numeric

Status: Accepted · Date: 2026-10-22 · Spec: §7 «Локализация»; amends the «Formats» point of ADR-0009

## Context

ADR-0009 takes every format from `Intl`, with `ka-GE` for Georgian. While building the
links screens, desktop Chrome 155 on Linux turned out to carry no Georgian data at all:
`Intl.DateTimeFormat.supportedLocalesOf(['ka', 'ka-GE'])` is empty. Intl then falls back to
American English without a word, so a Georgian sentence read «ბმული მოქმედებს Oct
25-მდე», and an amount would read «1,712.33». Telegram's clients on Android and Windows
show Mini Apps in Chromium-based WebViews, which may be just as bare. iOS and macOS have
the data.

Georgian also attaches case endings to the date itself: «25 ოქტომბრამდე» ("until 25
October"). A month name from Intl can't take an ending, but a numeral takes one with a
hyphen: «25.10-მდე».

## Decision

- **Numbers.** Georgian formats with `ru-RU`, which writes them the way Georgian does:
  «1 712,33», with a non-breaking space to group and a comma for decimals.
- **Dates.** Georgian dates are numeric, day before month, also through `ru-RU`:
  «25.10», and «25.10.2026» where the year matters. Russian and English keep their
  month names, «25 октября» and «25 October».
- The bot's own formatter (ADR-0014) follows the same rules.
- Country and currency names come with the orders slice. Where Intl has no Georgian
  names for them, Georgian gets the few we use from its dictionary.

## Consequences

- Every device shows Georgian the same way, whatever its Intl carries.
- Georgian sentences put endings on numerals, «{date}-მდე», which is ordinary written
  Georgian.
- A unit test pins the Georgian date format, so a change to it is a decision rather
  than an accident.

## Alternatives considered

- **Trusting Intl with `ka-GE`.** American English inside Georgian sentences on some
  devices.
- **Georgian month names in the dictionary**, formatted by hand. Each one would need its
  case forms for every sentence that holds a date.
- **Detecting support and switching formats.** Two different looks for the same user on
  two devices.
