# Swap — delivery plan

Phases are strictly sequential (§12). A phase starts only after the previous one's
acceptance criteria are met and the owner has confirmed. This file holds the current
phase's checklist and the estimates. Phase 1's order is ADR-0006.

A **session** here is one sitting of mine that ends in reviewable PRs with green CI,
roughly 2–4 hours of wall-clock work.

## Phase 0 — skeleton (accepted 2026-10-22)

Phase 0 is done when (the kickoff's DoD and §12, with the owner's answers of
2026-10-21):
- `docker compose up` locally brings up Caddy, api, worker and postgres;
- `/healthz` answers on api and worker;
- the Mini App opens from `@peertopeerswapbot` on the owner's phone and greets the
  owner by Telegram name, read from `/api/v1/me` after server-side `initData`
  validation, in the language they pick: Russian, English or Georgian;
- CI is green, `alembic upgrade head` runs on start, and ruff, mypy, eslint and
  prettier are clean.

### Owner

- [x] Answer `docs/QUESTIONS.md` parts A and B (2026-10-21).
- [x] Log the bot out of the cloud Bot API (2026-10-21).
- [x] BotFather: groups off; Main Mini App on, fullscreen, at
      `https://swap.latentstate.dev` (2026-10-21).
- [x] DNS: an A record for `swap.latentstate.dev` → the VPS, DNS only (grey cloud). I
      created it on 2026-10-21 with the owner's Edit-DNS token.
- [x] Once it is deployed: open the app from the bot on your phone, and say whether
      phase 0 is accepted. The owner signed in from his phone and accepted it on
      2026-10-22.

### Me

**PR 1 — docs.** QUESTIONS with the answers, ADRs 0001–0011, this plan, CLAUDE.md, the
README and the licence.

**PR 2 — backend skeleton and CI**
- [x] `backend/`: a uv project on Python 3.12; a FastAPI app factory; pydantic-settings;
      structlog with redaction; RFC 9457 problems with machine codes; the security
      headers (ADR-0001); `/healthz`.
- [x] SQLAlchemy 2 async and Alembic with the naming convention. Migration 0001 creates
      `users`, `sessions` and `service_heartbeats`.
- [x] pytest on real Postgres with a transaction per test; mypy strict.
- [x] CI: ruff, ruff format, mypy, pytest, `alembic upgrade → downgrade → upgrade`,
      gitleaks.

**PR 3 — auth, bot, worker**
- [x] `initData` validation, tests first: a valid string, a tampered field, the wrong
      token, a missing hash, duplicate keys, too old, from the future, URL-encoding
      edge cases, and `signature` kept in the check string.
- [x] `POST /api/v1/auth/telegram`, `GET /api/v1/me`, and `PATCH /api/v1/me` for the
      language.
- [x] The worker: Starlette with an APScheduler heartbeat, `/healthz`, and the relay
      endpoint `/message`. `/start` answers with an «Открыть Swap» button in the
      user's language. At start the worker sets the bot's profile texts and its menu
      button (ADR-0008, ADR-0009).

**PR 4 — frontend**
- [x] Vite, React 18, strict TypeScript, Tailwind v4 on Telegram's theme variables,
      TanStack Query, react-router 7 (memory router), and `@tma.js/sdk-react` 3.x for
      theme, BackButton and fullscreen safe areas.
- [x] ru/en/ka dictionaries and the language switch; the hello screen; «Откройте в
      Telegram» everywhere else.
- [x] The generated API client (ADR-0007). CI: eslint, prettier, tsc, vitest, build, the
      300 KB budget and the OpenAPI drift check.

**PR 5 — Docker, compose, deploy**
- [x] One image. `docker-compose.yml` runs caddy, api, worker and postgres on
      10.89.91.0/24. Add `compose.sh`, `logs.sh`, `test.sh`, and
      `swap.tools.dev_launch` for testing in Chrome.
- [x] `deploy/docker-compose.vps.yml`: api on `mcp-shared`; the worker in the host's
      network on `127.0.0.1:8707`; the db published on `127.0.0.1:5436` for it.
      Add `deploy/Caddyfile-swap.caddy` and `deploy/vps.sh`.
- [x] On the VPS: clone, write `.env`, deploy (2026-10-21).
- [x] Register the bot in `bots.json` and restart the relay, then check every bot's
      webhook. All five came back within 2 s, with nothing pending.
- [x] Append the Caddy block, validate, reload, and probe every site before and after.
      All 17 other sites answered exactly as before. Let's Encrypt issued Swap's
      certificate within 4 s.

Expected later in phase 1, not now: a rate limit on auth, a session cleanup job,
plurals, and backups (slice 7).

## Estimates

| Phase | Sessions | Calendar |
|---|---|---|
| 0 — skeleton | 4 | 1–2 days, plus the owner's DNS record and phone check |
| 1 — MVP | ≈ 18 | ≈ 4 weeks; the last days wait on the group's real deal |

On 2026-10-21 phase 1 grew by about two sessions: every string in three languages,
and saved payment details.

Phase 1 by slice (ADR-0006):

| Slice | Sessions |
|---|---|
| Links | 1.5 |
| Orders | 2 |
| Deals, the state machine, payment details | 3 |
| Notifications | 1 |
| **Demo** | **≈ 7.5** |
| Balances and lists | 1 |
| Documents through the bot | 1.5 |
| Cancel, dispute, notes | 1 |
| Reminders, expiry, feed | 1.5 |
| Manual rate, profile, blocks, deletion | 1.5 |
| Backups, hardening, agreement | 1.5 |
| Georgian review, acceptance fixes | 1.5 |
| **Total** | **≈ 18** |
