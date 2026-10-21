# 0011. Phase-0 platform: sessions, router, tooling, logs and deploy

Status: Accepted · Date: 2026-10-21 · Spec: §7, §8, §9; Q-A4, Q-A5

Phase 0 needs five small decisions that another engineer would ask about. Each is
the smallest thing that works (the owner: no overengineering).

## Sessions (Q-A4)

- `POST /api/v1/auth/telegram` validates `initData` with our own function: the HMAC,
  and an age of at most an hour. It returns an opaque token, and the database keeps
  only its SHA-256.
- A session lives 24 h and belongs to one launch. The Mini App gets fresh `initData`
  every time it opens, so the token is held in JS memory only and sent as
  `Authorization: Bearer`.
- A 401 re-authenticates once with the launch's `initData`. If that is too old, the
  app asks the user to reopen it.
- No cookies, so no CSRF and no third-party-cookie rules in Telegram Web. The spec's
  30-day sliding expiry was meant for a cookie that outlives the app, which this token
  never does.

## Router

react-router 7 with a memory router. Telegram has no address bar, the launch
parameters live in the URL's hash, and the BackButton drives history. A deep link,
such as an invite or a deal, arrives as a launch parameter and becomes the router's
first entry.

## Python tooling

- uv 0.13, pinned in CI and in the Dockerfile, with a lock file.
- ruff for lint and format, and mypy strict on the whole `swap` package.
- pytest against real Postgres 16, with a transaction per test.

The same commands run in CI and on a laptop.

## Logs

structlog writes JSON in production and console lines in dev. One processor redacts
three things: denylisted keys (tokens, `init_data`, payment details), anything shaped
like a bot token, and the configured token itself, so a Bot API URL inside an
exception can't leak it. Request and response bodies are never logged.

## Deploy (Q-A5)

- One image. The frontend build stage feeds the Python stage, and api, worker and
  migrate are that image with different commands.
- The image is built on the VPS, as phonyx's are, by `deploy/vps.sh`: pull, build, a
  `pg_dump` before migrating, migrate, recreate api and worker, wait for health. The
  box is small and shared, so the build caps Node's heap.
- Rollback is `git checkout <previous> && ./deploy/vps.sh`, plus restoring the dump if
  a migration ran.
- No dev tunnel. I work in desktop Chrome with launch parameters signed by
  `python -m swap.tools.dev_launch`, which the server validates like any others. The
  owner tests in Telegram once a change is on the VPS.
