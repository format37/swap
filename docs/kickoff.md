# Swap — kickoff for the implementing agent

You are the implementing engineer for **Swap**, a Telegram Mini App that lets people who know each other plan counter-transfers of currency across countries. The owner (Alex, GitHub `format37`) is the product owner and reviewer. This file is your first instruction; the full specification is in `docs/tech-specs.md` (Russian; UI strings are Russian too — you can read both).

## What Swap is, in four sentences

A user announces an intent: "next week I will have RUB in Russia; I want GEL or USD in Georgia." People who are linked to that user by personal invitation see the intent and can propose a deal: I send your RUB to my grandmother's card, you hand me GEL in Tbilisi. The app walks the deal through a strict state machine until both sides have pressed "Received", attaches statements as proof, and shows who owes whom right now. The app never holds, moves, or guarantees money — it plans and records.

## Decisions that are final

- Name: **Swap**. Telegram bot already exists: `@peertopeerswapbot`, display name "swap". The owner will hand you the token for a separate *test* bot; never register a webhook on the production bot without explicit approval.
- Format: Telegram Mini App, mobile-first (360–430 px). Plain-browser visitors get a stub until v1.
- Trust model: one-to-one **links** established by invitation (invite link or `@username` request). No circles, groups, roles, or public listing. An order is visible only to the author's active links. Links are not transitive.
- Stack: Python 3.12 + FastAPI + aiogram 3, SQLAlchemy 2 (async) + Alembic, PostgreSQL 16, APScheduler in a separate `worker` process; React 18 + TypeScript + Vite + Tailwind + TanStack Query + `@telegram-apps/sdk-react`; Docker Compose behind Caddy on the owner's VPS (Ubuntu), domain `swap.latentstate.dev` (path-style `latentstate.dev/swap` is allowed if you find a technical reason — record it in an ADR).
- Money is `NUMERIC(18,2)` in Postgres and `Decimal` in Python. Never `float`.
- Deal state changes go only through the state-machine service and write an `Event` row in the same transaction.
- Scope boundaries in SPEC §2 are product policy, not a backlog: do not add public order boards, cross-user search, reputation, escrow, or anything that would make Swap an exchange.

## Repository layout (monorepo)

```
backend/    FastAPI app, aiogram bot, alembic, tests
frontend/   Vite app
deploy/     docker-compose.yml, Caddyfile, release.sh, backup/
docs/       tech-specs.md (this spec), adr/NNNN-title.md, QUESTIONS.md
CLAUDE.md   conventions for yourself: commands, layout, rules below
```

## How to work

1. **Read `docs/tech-specs.md` end to end before writing any code.**
2. **Before code, produce three things and stop for review:**
   - `docs/QUESTIONS.md` — everything ambiguous or that you disagree with, each with your proposed default so the owner can answer "ok" in one word.
   - Your choices for every row of SPEC §13 "Решает разработчик", each as a one-page ADR in `docs/adr/`.
   - A phase-0 plan as a checklist, plus a rough estimate in working sessions for phase 0 and phase 1 (SPEC §12).
3. Work phase by phase (SPEC §12): phase 0 skeleton → phase 1 MVP → v1 → v2. Do not start a phase before the previous one's acceptance criteria are met and the owner has confirmed.
4. First demonstrable slice inside phase 1: **link + order + deal without documents**, running on the test bot. Show it before building the rest.
5. Commit small, with messages that say *why*. Open a PR per feature; the owner reviews within a day. CI (GitHub Actions) must run tests and linters on every PR and stay green.
6. Tests are not optional for: the deal state machine (every transition, every illegal transition), object-level authorization (a user outside a link cannot read an order or deal — write the negative tests first), amount calculation from `rate_spec`, rate-source parsing, `initData` validation.
7. Any decision not in the spec that another engineer would ask about goes into `docs/adr/` as a one-page "what we decided and why". Never leave it only in chat.
8. Write `CLAUDE.md` in the repo root on day one and keep it current: how to run the stack, run tests, run migrations, the rules in this file.

## Hard rules

- Secrets only in `.env` on the machine; commit `.env.example` only. If you ever see a token in a file you are about to commit, stop.
- Do not deploy to the VPS, change DNS, or touch Caddy on the production host without the owner saying so in the current session. Local `docker compose up` is always fine.
- Recipient details (card numbers, phone numbers for transfers) are encrypted at the application layer before they reach the database and are masked in every log line and API response except to the leg's payer.
- No analytics or third-party scripts in the frontend. Error reporting (Sentry) is v1 and needs the owner's DSN.
- Russian is the only UI language in MVP, but every user-facing string lives in a dictionary from the first commit.
- When the spec and this file conflict, this file wins; when you think both are wrong, say so in `QUESTIONS.md` before building around it.

## What the owner will give you on request

- Test bot token; later the production bot token.
- SSH access to the VPS and a DNS record for `swap.latentstate.dev` (phase 0, once local setup works).
- S3-compatible bucket credentials for backups.
- Himself and three acquaintances as the acceptance group: MVP is accepted when they run one real deal end to end, order to double "Received".

## Definition of done for phase 0

- `docker compose up` locally brings up Caddy, api, worker, postgres.
- `/healthz` on api and worker.
- Mini App opens from the test bot on the owner's phone and shows his Telegram name after `initData` validation.
- CI green; `alembic upgrade head` runs on start; `ruff`, `mypy`, `eslint`, `prettier` clean.

Start with step 1. Reply with your questions, ADR drafts, and the phase-0 checklist.
