# CLAUDE.md — Swap

Swap is a Telegram Mini App for planning counter-transfers of currency between people
linked by personal invitation. It plans and records; it never holds, moves or
guarantees money.

Read before changing anything:

- `docs/kickoff.md` holds the owner's kickoff instructions, verbatim. The hard rules
  below come from it.
- `docs/tech-specs.md` is the spec, in Russian (UI strings are Russian too). FR-x.y
  numbers are used in tasks and tests.
- `docs/QUESTIONS.md` holds the open questions and the owner's answers. An answer
  there overrides the spec.
- `docs/adr/` has every decision another engineer would ask about, one page each.
  Never leave a decision only in chat.
- `docs/plan.md` has the phases, the current phase's checklist and the estimates.

Precedence: the owner's answer in QUESTIONS, then the kickoff rules below, then the
spec. When both look wrong, write a question before building around it.

## Status

Phase 0 has not started. PR 0 (QUESTIONS, ADRs 0001–0007, plan) is waiting for the
owner's review.

## Commands

None yet. The phase-0 PRs add them here, following the owner's house scripts:
`./compose.sh`, `./logs.sh <service>`, `./test.sh [backend|frontend] [pytest args]`,
and Alembic through `docker compose exec api alembic …`.

## Hard rules

- **Secrets live only in `.env`.** Only `.env.example` is committed. Stage explicit
  paths (never `git add -A`) and read `git diff --cached` before every commit. If a
  token is in a staged file, stop.
- **The token in this machine's `.env` belongs to the PRODUCTION bot
  `@peertopeerswapbot`** (checked with `getMe` on 2026-10-21). That holds until the
  owner swaps in a test bot. Call no state-changing Bot API method with it: no
  `setWebhook`, `deleteWebhook`, `setChatMenuButton`, `getUpdates` or `sendMessage`.
  Code guards webhook registration from PR 2 on.
- **No deploy to the VPS, no DNS change and no edit of `~/reverse-proxy/Caddyfile`**
  unless the owner says so in the current session. Local `docker compose up` is
  always fine.
- **Money is `NUMERIC(18,2)` in the database, `Decimal` in Python and a string in
  JSON.** Never `float`, not in tests and not in the UI: format with
  `Intl.NumberFormat` from the string, and let the api do the arithmetic.
- **Deal status changes only through the state-machine service**, with an `events`
  row in the same transaction. A database trigger enforces this (ADR-0002).
- **Recipient details are encrypted in the app before they reach the database**
  (ADR-0004). They are masked in every log line and every API response, except for
  the people Q-B8 allows.
- **No analytics and no third-party scripts in the frontend.** Sentry comes in v1,
  with the owner's DSN.
- **Every user-facing string lives in a dictionary**, UI and bot alike. Russian is
  the only language in the MVP.
- **§2 is product policy.** No public order board, no search among strangers, no
  reputation, no escrow, nothing that makes Swap an exchange. Visibility is active
  links only, and links are not transitive.
- **Tests are not optional for** the deal state machine (every transition and every
  illegal one), object-level authorization (negative tests first), amounts from
  `rate_spec`, rate-source parsing and `initData` validation.
- **Phases are gated.** A phase starts only after the previous one is accepted and
  the owner has confirmed. The first demo inside phase 1 is link + order + deal
  without documents, on the test bot.
- **One PR per feature, with CI green.** Commits are small, and each message says
  why.

## Layout (target)

```
backend/    FastAPI app, aiogram bot, worker, alembic, tests
frontend/   Vite app
deploy/     VPS compose, Caddy site block, release.sh, backup/
docs/       spec, QUESTIONS, adr/, plan
```

## Environment facts

- **This box.** Python 3.12 comes through `uv python`; the system `python3` is 3.11.
  Node is 26, Docker 29, Compose v5. Ports already taken here: 3000, 5173, 5433,
  5434, 5439, 8000, 8010, 8018, 8020, 8080. Swap's local ports go elsewhere
  (planned: Caddy 8030, db 5436). The local compose subnet is 10.89.91.0/24, free on
  2026-10-21; other projects pin 10.89.x.0/24.
- **VPS (OVH).**
  - A shared Caddy 2.8, `reverse-proxy`, owns :80/:443 and reaches apps over the
    external `mcp-shared` network. App containers publish no host ports.
  - A new hostname gets its certificate automatically if its Cloudflare A record is
    grey-cloud.
  - The Caddyfile is bind-mounted, so edit it in an inode-preserving way (vim,
    `cat >>`), never with `sed -i`.
  - Docker's default address pool on the box is nearly exhausted, so pin a subnet
    and check it on the box first.
  - Runbook: the `ovh` skill.
- **GitHub.** Account `format37`; the repo is private.
