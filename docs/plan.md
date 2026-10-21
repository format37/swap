# Swap — delivery plan

Phases are strictly sequential (§12). A phase starts only after the previous one's
acceptance criteria are met and the owner has confirmed. This file holds the phase-0
checklist and the estimates. Phase 1's order is ADR-0006.

A **session** here is one sitting of mine that ends in a reviewable PR with green CI,
roughly 2–4 hours of wall-clock work. Owner review is assumed within a day (kickoff).

## Phase 0 — skeleton

Phase 0 is done when (kickoff DoD and §12):
- `docker compose up` locally brings up Caddy, api, worker and postgres;
- `/healthz` answers on api and worker;
- the Mini App opens from the **test** bot on the owner's phone and shows the owner's
  Telegram name, read from `/api/v1/me` after server-side `initData` validation;
- CI is green, `alembic upgrade head` runs on start, and ruff, mypy, eslint and
  prettier are clean.

### Owner, before or during phase 0

- [ ] Answer `docs/QUESTIONS.md` part A. "ok" per item is enough.
- [ ] Create the test bot in BotFather, put its token in `.env` as
      `TELEGRAM_BOT_TOKEN`, and take the production token out of this machine's
      `.env` (Q-A1).
- [ ] Say go for the private GitHub repo (Q-A2).
- [ ] For the VPS step: the grey-cloud A record `swap` → the VPS, SSH as for phonyx,
      a GHCR read token on the box, and an explicit go for the deploy and the Caddy
      edit.

### Me

**PR 0 — docs** (this one): QUESTIONS, ADRs 0001–0007, this plan, CLAUDE.md.

**PR 1 — repo, backend skeleton, CI** (session 1)
- [ ] Private repo, with `main` protected (PR and green CI required) and a PR
      template that asks "why".
- [ ] `backend/`: a uv project on Python 3.12 with a FastAPI app factory,
      pydantic-settings (blank means unset), structlog JSON logs with the redaction
      processor (ADR-0004), and RFC 9457 problem responses with machine codes. The
      processor also scrubs anything shaped like a bot token, because Bot API URLs
      (including file downloads) embed it. HTTP-client request logging stays off.
- [ ] SQLAlchemy 2 async and Alembic with the naming convention (ADR-0002). The first
      migration creates `users` and `sessions`. `alembic upgrade head` runs as a
      one-shot `migrate` service that api and worker wait for.
- [ ] `/healthz`: database ping and worker heartbeat age.
- [ ] pytest against real Postgres 16 with a transaction per test; mypy strict on
      `swap.domain`.
- [ ] CI: ruff check, ruff format --check, mypy, pytest,
      `alembic upgrade head → downgrade -1 → upgrade head`, gitleaks. The frontend
      jobs come with PR 3.
- [ ] pre-commit: ruff, prettier, gitleaks, a large-file guard.

**PR 2 — auth, bot, worker** (session 2)
- [ ] `initData` validation as our own function (§8). Tests first: a valid string, a
      tampered field, the wrong token, a missing hash, duplicate keys, `auth_date`
      more than 1 h old or in the future, and URL-encoding edge cases. The
      `signature` field stays in the check string, and only `hash` is excluded, as
      in the Bot API docs. aiogram's helper doesn't check `auth_date` at all.
- [ ] `POST /api/v1/auth/telegram` upserts the user and opens a session (transport per
      Q-A4). Then `GET /api/v1/me` and a rate limit on auth.
- [ ] aiogram 3 on `/tg/webhook`, with the secret-token header and `allowed_updates`
      set to message and callback_query. `/start` greets with an «Открыть приложение»
      web-app button. Strings come from the dictionary.
- [ ] Webhook registration happens on start only when `TG_SET_WEBHOOK=1`, and is
      refused for `@peertopeerswapbot` unless `TG_ALLOW_PROD_BOT=1` is also set (the
      token currently in `.env` belongs to the production bot).
- [ ] Worker: an APScheduler process (ADR-0005) with a heartbeat job, the
      advisory-lock singleton and its own `/healthz`.

**PR 3 — frontend** (session 3)
- [ ] Vite, React 18 and strict TypeScript, Tailwind v4 mapped to the Telegram theme
      variables (ADR-0003), TanStack Query, and react-router 7 (the router phonyx
      uses; ADR in the PR).
- [ ] Telegram SDK (`@tma.js/sdk-react`, Q-A8) init: `expand()`, theme binding,
      BackButton, launch params. In a plain browser, show «Откройте через Telegram»
      with a link to the bot.
- [ ] A typed `ru` dictionary from the very first string, with plurals through
      `Intl.PluralRules`.
- [ ] The generated API client (ADR-0007) and a hello screen, «Привет,
      <display_name>», from `/me`.
- [ ] Dev in a desktop browser through the SDK's mocked environment, with `initData`
      signed by the **test** bot's token (`scripts/dev_init_data.py`). The server
      validates it for real; the code has no auth bypass.
- [ ] CI: eslint, prettier --check, tsc, vitest, build, the 300 KB gzip budget, and
      the OpenAPI drift check.

**PR 4 — local stack and the phone** (session 3, continued)
- [ ] One image for api, worker and migrate: a multi-stage build from the frontend
      build to Python. `docker-compose.yml` runs `caddy:2.8`, api, worker and
      postgres:16 on the pinned subnet 10.89.91.0/24, with host ports clear of the
      ones this box already uses.
- [ ] `compose.sh`, `logs.sh` and `test.sh`, the owner's house scripts.
- [ ] A tunnel per Q-A5, and a script that points the **test** bot's menu button and
      webhook at it.
- [ ] A phone check on the owner's device(s) through the tunnel. Also check Bot API
      10.2's rule that blocks Mini App methods called from a domain other than the
      app's own, against both the tunnel URL and the production URL.

**PR 5 — VPS** (session 4, only after the owner's go)
- [ ] `deploy/docker-compose.vps.yml` (expose-only, on `mcp-shared`, with a pinned
      subnet checked free on the box), `deploy/Caddyfile-swap.caddy`,
      `deploy/release.sh` (pull, pre-migration `pg_dump`, migrate, up) and
      `deploy/README.md`. Images come from GHCR, built by CI on a tag.
- [ ] `.env` on the VPS from `.env.example`. Point the test bot's Main Mini App and
      webhook at `https://swap.latentstate.dev`.
- [ ] Acceptance on the owner's phone, plus iOS, Android and Desktop where available
      (§13 risks).

ADRs expected during phase 0: session transport (after Q-A4), router, i18n, Python
tooling (uv), logging, dev tunnel, deploy and rollback.

## Estimates

| Phase | Sessions | Calendar, with reviews within a day |
|---|---|---|
| 0 — skeleton | 4 | 2–4 days, plus the owner's bot, DNS and SSH tasks |
| 1 — MVP | ≈ 16 | ≈ 3–4 weeks; the last days wait on the group's real deal |

Phase 1 by slice (ADR-0006):

| Slice | Sessions |
|---|---|
| Links | 1.5 |
| Orders | 2 |
| Deals and the state machine | 2.5 |
| Notifications | 1 |
| **Demo** | **≈ 7** |
| Balances and lists | 1 |
| Documents through the bot | 1.5 |
| Cancel, dispute, notes | 1 |
| Reminders, expiry, feed | 1.5 |
| Manual rate, profile, blocks, deletion | 1.5 |
| Backups, hardening, agreement | 1.5 |
| Acceptance fixes | 1 |
| **Total** | **≈ 16** |

These figures assume the defaults in `QUESTIONS.md` are accepted. A different answer
on the state machine (Q-B1) or the balance (Q-B2) adds up to a session to slice 1 or
slice 2.
