# CLAUDE.md — Swap

Swap is a Telegram Mini App for planning counter-transfers of currency between people
linked by personal invitation. It plans and records; it never holds, moves or
guarantees money.

**This repository is public** (github.com/format37/swap, MIT). Everything committed is
published.

Read before changing anything:

- `docs/kickoff.md` holds the owner's kickoff instructions, verbatim. Most of the hard
  rules below come from it.
- `docs/tech-specs.md` is the spec, in Russian. FR-x.y numbers are used in tasks and
  tests.
- `docs/QUESTIONS.md` holds the questions and the owner's answers. An answer there
  overrides the spec and the kickoff. Part D lists the owner's own decisions of
  2026-10-21, part F his notes after his first test on 2026-10-22, part G his notes
  after the demo with others, and part H his notes after the first real deal, both the
  same day.
- `docs/adr/` has every decision another engineer would ask about, one page each.
  Never leave a decision only in chat.
- `docs/plan.md` has the current phase's checklist and the estimates.

Precedence: the owner's answer in QUESTIONS, then the kickoff rules, then the spec.
When both look wrong, write a question before building around it.

## Status

The owner accepted phase 0 (skeleton) on 2026-10-22; it is live at
https://swap.latentstate.dev. Phase 1 (MVP) started on 2026-10-22, slice 1 first
(ADR-0006). Its checklist, PR by PR, is in `docs/plan.md`.

## Commands

- `./test.sh` runs every suite; `./test.sh backend [pytest args]` runs the backend's.
  It starts the compose db (`127.0.0.1:5436`) and uses a `swap_test` database that
  the suite migrates from scratch on every run.
- In `backend/`: `uv run ruff check . && uv run ruff format --check .`, `uv run mypy`,
  and `uv run python -m swap.tools.openapi` (prints the schema).
- Migrations: `DATABASE_URL=postgresql+asyncpg://swap:swap@127.0.0.1:5436/swap uv run
  alembic upgrade head`, and `uv run alembic check` to compare models with the schema.
- In `frontend/` (Node 24 in CI): `npm ci`; `npm run lint && npm run format:check`;
  `npx vitest run`; `npm run build && npm run budget` (300 KB gzip, ADR-0003).
- The API contract (ADR-0007): `uv run python -m swap.tools.openapi >
  ../frontend/openapi.json` in `backend/`, then `npm run gen:api` in `frontend/`.
  Commit both files; CI fails when they drift from the api.
- Trying the app in a desktop browser: run the api (compose, or uvicorn on the host),
  then `SWAP_API=http://127.0.0.1:<api port> npm run dev` (Vite on 5180). Print a
  signed launch URL with `TELEGRAM_BOT_TOKEN=… uv run python -m swap.tools.dev_launch
  --base http://127.0.0.1:5180` and open it with mobile emulation. The api validates
  it like a real launch, and it expires in an hour. A URL that differs only in its hash
  doesn't reload the page, so reload by hand.
- Run `git config core.hooksPath .githooks` once per clone. The pre-commit hook then
  refuses staged bot tokens and `.env` values.

Python runs through uv 0.13 (pinned in CI and in the Dockerfile, and required by
`backend/pyproject.toml`). This box has uv 0.7.2, so here prefix commands with
`UV="uvx --from uv==0.13.4 uv"` for `./test.sh`, or run `uvx --from uv==0.13.4 uv …`
directly.

- `./compose.sh [--fresh]` builds and starts the local stack: Caddy on
  http://127.0.0.1:8030, api, worker and Postgres, with migrations on every start.
  `./logs.sh [service]` follows its logs. Outside Telegram the app shows its stub;
  open it with a signed launch URL (above) to see more.
- Deploying: `deploy/README.md`. The routine is `./deploy/vps.sh --pull` on the VPS,
  with the owner's go.

## Hard rules

- **Secrets live only in `.env`.** Only `.env.example` is committed. Stage explicit
  paths (never `git add -A`) and read `git diff --cached` before every commit. If a
  token is in a staged file, stop. The repo is public, so a pushed secret is a leaked
  secret: rotate it, don't just delete it.
- **Nothing about the VPS beyond what the deploy files need.** No IP addresses,
  passwords or host details in the repo. Firewall rules, free memory and the like
  stay out too.
- **There is one bot, `@peertopeerswapbot`, the production bot** (the owner,
  2026-10-21). It is logged out of the cloud Bot API and served by the VPS's own Bot
  API server through the owner's relay (ADR-0008).
  - **Never call `api.telegram.org` with its token.** Once the 10-minute grace period
    is over, a call logs the bot back in to the cloud, and its updates stop reaching
    the relay without an error anywhere.
  - Nothing outside the VPS talks to Telegram: `TELEGRAM_API_BASE` stays unset
    locally and in CI.
- **The shared VPS services belong to the owner.** `~/reverse-proxy/Caddyfile` serves
  other sites, and `~/telegram_bot/bots.json` serves other bots. When changing either:
  - only with the owner's go in the current session;
  - back the file up first;
  - edit it inode-preserving (`cat >>`, Python `r+`), never with `sed -i`;
  - validate before the reload or restart;
  - check the other sites and bots afterwards.
- **No deploy to the VPS and no DNS change** unless the owner says so in the current
  session. Local `docker compose up` is always fine.
- **Money is `NUMERIC(18,2)` in the database, `Decimal` in Python and a string in
  JSON.** Never `float`, not in tests and not in the UI: format with
  `Intl.NumberFormat` from the string, and let the api do the arithmetic.
- **Deal status changes only through the state-machine service**, with an `events`
  row in the same transaction. A database trigger enforces this (ADR-0002).
- **Swap stores no payment details** (ADR-0021). A deal says which currency, how
  much, by when and how (cash, bank or crypto); where to pay is the parties' own
  business, and a proposal's comment can carry it.
- **No analytics and no third-party scripts in the frontend.** Sentry comes in v1,
  with the owner's DSN.
- **Every user-facing string lives in a dictionary, in Russian, English and Georgian**
  (ADR-0009), UI and bot alike. A PR that adds a string adds all three.
- **§2 is product policy.** No public order board, no search among strangers, no
  reputation, no escrow, nothing that makes Swap an exchange. Visibility is active
  links only, and links are not transitive.
- **Tests are not optional for** the deal state machine (every transition and every
  illegal one), object-level authorization (negative tests first), amounts from
  `rate_spec`, rate-source parsing and `initData` validation.
- **Phases are gated.** A phase starts only after the previous one is accepted and
  the owner has confirmed. The first demo inside phase 1 is link + order + deal
  without documents.
- **One PR per feature, with CI green.** Commits are small, and each message says
  why.
- **No overengineering** (the owner): the smallest thing that works, then iterate.

## Layout (target)

```
backend/    FastAPI app (api), worker with the bot, alembic, tests
frontend/   Vite app
deploy/     VPS compose, Caddy site block, vps.sh
docs/       spec, kickoff, QUESTIONS, adr/, plan
```

## Environment facts

- **This box.** Python 3.12 comes through `uv python`; the system `python3` is 3.11.
  Node is 26, Docker 29, Compose v5. Ports already taken here: 3000, 5173, 5433,
  5434, 5439, 8000, 8010, 8018, 8020, 8080. Swap's local ports: Caddy 8030, db 5436,
  Vite 5180. The local compose subnet is 10.89.91.0/24; other projects pin
  10.89.x.0/24.
- **VPS (OVH).** Runbook: the `ovh` skill. Swap's own notes on it live in memory, not
  here.
  - The shared Caddy 2.8, `reverse-proxy`, owns :80/:443 and reaches apps over the
    external `mcp-shared` network.
  - A new hostname gets its certificate automatically if its Cloudflare A record is
    grey-cloud.
  - Anything in the host's network binds `127.0.0.1`, never `0.0.0.0`.
- **GitHub.** Account `format37`; the repo is public.
