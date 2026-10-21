# 0014. Notifications: an outbox row per recipient, written with the change, worded and sent by the worker

Status: Accepted · Date: 2026-10-22 · Spec: §7, §9 «Потоки» 2, §10 «Telegram: бот», FR-7.1; ADR-0002, ADR-0005, ADR-0008, ADR-0009

## Context

ADR-0002 made `notifications` both the Telegram outbox and the in-app feed. ADR-0005
gave the worker a sweep every 5 s, and ADR-0008 made the worker the only Telegram
client. Messages go out in the recipient's language (ADR-0009). ADR-0006 left bot
notifications for the last step of slice 1. But a request to an @username is invisible
without one, so the outbox arrives with links.

## Decision

**A message is written in the same transaction as its change.** A service that changes
state calls `notify(db, recipient, type, params, target)`. If the change rolls back,
the message goes with it; if it commits, the message will be sent.

**A row holds data, not text.**
- `type`, such as `link.requested` or `deal.accepted`;
- `params`, JSONB with what the words need: names, amounts as strings, currency codes;
- `target`, the card that «Открыть» opens (ADR-0013).

The worker words the message when it sends it, in the recipient's language at that
moment, from `swap/i18n.py`. Payment details never enter `params`: a message names
their kind and title only.

**Each row is one message** in plain text, with no parse mode, so a name can't break
any markup. It has one «Открыть» button to its target.

**Sending.** Every 5 s, the worker claims due rows one at a time with
`FOR UPDATE SKIP LOCKED`, sends each, and records the outcome in the same short
transaction:
- success: `sent`, with `tg_message_id`;
- 429: due again after `retry_after`;
- 403, because the user blocked the bot or never started it: `can_message` turns off
  and the row is `skipped`;
- any other failure: `attempts` goes up and the row is due again after
  30 s × 2^attempts, an hour at most. After 8 attempts it is `failed`.

A recipient whose `can_message` is off is `skipped` without a call. Without
`TELEGRAM_API_BASE`, locally and in CI, the sweep isn't scheduled and rows stay
pending.

**Delivery is at least once** (ADR-0005). `dedup_key`, unique where set, makes one-off
messages idempotent. Reminders use it in slice 5.

**The in-app feed** reads the same rows through `read_at` in slice 5. Skipped and
failed rows show there too.

**Amounts in the bot's text** go through a small formatter in `swap/i18n.py`, with
the separators of ru-RU, en-GB and ka-GE. The bot has no `Intl`.

## Consequences

- A fix to a message's wording reaches messages already queued, with no data
  migration.
- The api never calls Telegram, and tests assert the rows a change writes.
- If the worker dies between Telegram's answer and its commit, a message goes out
  twice.

## Alternatives considered

- **Wording the text when the row is written.** The language and the wording would be
  frozen at that moment.
- **Sending from the request** (FastAPI `BackgroundTasks`). Lost on a restart
  (ADR-0005).
- **A queue such as Redis.** Another component, for tens of messages a day.
