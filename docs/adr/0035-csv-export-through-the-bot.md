# 0035. The CSV export arrives as a file from the bot

Status: Accepted · Date: 2026-10-22 · Spec: FR-6.3; QUESTIONS K4; ADR-0008, ADR-0014

## Context

The owner asked for an export of every deal a person took part in, as CSV (K4). FR-6.3
put it in v1, and the owner pulled it forward. A download inside Telegram's WebView is
unreliable: some clients ignore it, and others open the file in a viewer with no way to
save it.

## Decision

**The bot sends the file.** `POST /me/export` queues an `export.deals` message for the
person, answering 202. The outbox makes the CSV when it sends it, so the file holds every
deal up to that moment. It goes to the person's chat as a document through the VPS's Bot
API server (ADR-0008), with a caption that counts the deals.
- **409 `export.no_chat`** when the bot may not write to them yet (Q-B12): the app
  tells them to press /start.
- **429 `export.too_soon`** when an export was asked for within the last minute.
- The export answers to no notification switch (ADR-0031): the person asked for it.

**The file.** One row per deal the person still keeps (ADR-0030), oldest first, in
`swap/export.py`. The columns:
- when it was proposed, accepted and closed, in their time zone;
- the order's number (ADR-0034);
- the status, and who it was with («Удалённый участник» for someone who left);
- what they gave and what they got: amount, currency, country and way;
- the rate, «1 GEL = 29.2 RUB», and where it came from.

Headers and words are in their language. Amounts stay decimal strings with a point,
as machines read them. The file is UTF-8 with a byte-order mark, so Excel reads the
Cyrillic and the Georgian right.

## Consequences

- The person keeps the file in their chat with the bot. Swap stores nothing more.
- Countries are ISO codes in the file: names would need a table the backend lacks.

## Alternatives considered

- **`WebApp.downloadFile`** (Bot API 8.0): a download from the app itself. Older
  clients lack it, and it needs a URL the file can be fetched from, with a session.
- **Showing the CSV as text to copy.** Copying hundreds of lines on a phone is no export.
