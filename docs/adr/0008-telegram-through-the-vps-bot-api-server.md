# 0008. Telegram goes through the VPS's own Bot API server and the owner's relay; the worker does all of it

Status: Accepted · Date: 2026-10-21 · Spec: §8, §9, §10; the owner's answer to Q-A1

## Context

The owner runs Telegram for his bots on the VPS and asked Swap to do the same as his
gptaidbot:

- `telegram-bot-api --local`, built from tdlib's source, runs as a systemd service and
  listens on `127.0.0.1:8081` only.
- The relay `bots_server_telegram` ([format37/telegram_bot]) runs in the host's
  network and owns the webhooks of every bot listed in `~/telegram_bot/bots.json`.
  At start it points each bot's webhook at itself and then POSTs every message to
  the bot's own server at `http://localhost:<PORT>/message`, with
  `Authorization: Bearer <token>`. The bot answers `{"type": "empty"}` and sends
  whatever it wants through `:8081` itself. Callback queries arrive the same way, as
  a reduced update. Edits are forwarded only to bots that opt in.
- The owner logged `@peertopeerswapbot` out of the cloud Bot API on 2026-10-21, as a
  local server requires. Since then, a call to `api.telegram.org` with its token
  (after the 10-minute grace period) would log it back in there, and its updates would
  stop reaching the relay without an error anywhere.

[format37/telegram_bot]: https://github.com/format37/telegram_bot

## Decision

1. **The worker is Swap's only Telegram client** (ADR-0005). On the VPS it runs in the
   host's network, so it can reach `127.0.0.1:8081`, and binds `127.0.0.1:8707`, the
   port registered for it in `bots.json` (the relay's other bots use 87xx). It reaches
   Postgres through the db container's port, published on `127.0.0.1:5436` only.
2. **Incoming.** `POST /message` checks the Bearer token in constant time, answers
   `{"type": "empty"}` at once, and feeds the update to aiogram's dispatcher in the
   background, as gptaidbot does, so the relay's thread is free again immediately.
   A reduced callback query gets the fields aiogram requires before it is validated.
3. **Outgoing.** aiogram's `Bot` on `TelegramAPIServer.from_base(TELEGRAM_API_BASE,
   is_local=True)`. `TELEGRAM_API_BASE` has no default. Local dev and CI leave it
   unset, and then the worker starts no bot and the outbox only logs. Nothing outside
   the VPS ever calls Telegram with this token.
4. **Swap never touches the webhook**; the relay owns it. At start the worker sets the
   commands, the descriptions and short descriptions in ru, en and ka (ADR-0009), and
   the menu button that opens the Mini App. All of these calls are idempotent.
5. **api never calls Telegram.** It validates `initData` with the token, which is pure
   HMAC and no network, and in phase 1 it queues notifications in the outbox.
6. **Files (slice 3).** In `--local` mode `getFile` returns an absolute path on the
   host, inside a directory named after the bot's token. The documents slice mounts
   it read-only the gptaidbot way, with a bind under `/mnt` and an ACL for the
   container's user. The path comes from `.env`, never from the repository.

## Consequences

- There is no public webhook endpoint. The origin serves only the Mini App and its
  API (ADR-0001).
- Swap depends on two shared host services. If either is down, /start goes unanswered
  and notifications wait in the outbox, which delivers at least once (ADR-0005). The
  Mini App itself keeps working.
- The relay forwards no `my_chat_member`, so a user who blocks the bot is noticed at
  the 403 on the next send (ADR-0005), not at once.
- Registering the bot is a one-time edit of `bots.json` and a restart of the relay.
  The restart re-sets the webhook of every bot on it, a few seconds' pause for the
  owner's other bots, whose updates wait in the Bot API server meanwhile. It happens
  once, with a backup, after Swap's worker is already listening, and every bot's
  webhook is checked afterwards.
- Local dev can't run the bot end to end. Tests post relay-shaped bodies to `/message`
  against a recording Bot API session, and the owner checks the real round trip on
  the VPS.
- To leave the local server: `logOut` through `:8081`, take the bot out of
  `bots.json`, and after 10 minutes the cloud API works again.

## Alternatives considered

- **The cloud Bot API with our own HTTPS webhook.** Standalone and simple, but not how
  the owner runs his bots, and it needs a public webhook path on the origin.
- **Our own webhook or long polling on the local server, bypassing the relay.** No
  relay restart, but then webhooks on the box would have two owners, and it isn't the
  pattern the owner asked for.
- **The relay's reply protocol** (`{"type": "text"}`, `"keyboard"`). It has no web_app
  buttons and can't send a message nobody asked for, which is what every Swap
  notification is.
