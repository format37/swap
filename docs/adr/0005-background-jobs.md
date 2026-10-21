# 0005. APScheduler in a singleton worker; every job is an idempotent sweep over database state

Status: Proposed · Date: 2026-10-21 · Spec: §7 «Фоновые задачи», §8, §9 «Потоки», §13 row 5

## Context

The jobs: send notifications, expire proposals (48 h) and orders, remind about legs
coming due (FR-6.2), purge recipient details, documents and deleted accounts on
schedule (§5, FR-5.5, §3), and in v1 refresh rates. §7 requires them to be
idempotent and to survive restarts. §8 picked APScheduler in a separate `worker`
process; §13 leaves `pg_cron` as the alternative.

## Decision

- **The worker is the api image with a different command.** It is a small Starlette
  app under uvicorn, and its lifespan starts APScheduler's `AsyncIOScheduler`. That
  makes the worker's `/healthz` an ordinary route on an internal port. The version is
  APScheduler 3.11, the stable line, pinned in `uv.lock`. 4.0 is still an alpha
  (4.0.0a6).
- **Jobs are sweeps, and the scheduler holds no state.** The schedule lives in code,
  with the in-memory job store. Each job selects what is due and not yet done, acts,
  and marks it done, in short transactions that claim rows with
  `FOR UPDATE SKIP LOCKED`. What makes a job idempotent lives in the domain tables,
  never in the scheduler. So a restart, a crash or a missed tick loses nothing: the
  next sweep picks up whatever is still due. Every job runs with `coalesce=True` and
  `max_instances=1`.
- **One worker at a time.** At start the worker takes a Postgres advisory lock.
  Without the lock it idles and retries, so two containers overlapping during a
  deploy cannot send twice.
- **Timed state changes go through the state machine.** Proposal expiry calls the
  same service as user actions, so it is journaled like everything else (ADR-0002).

| Job | Runs every | What makes it idempotent |
|---|---|---|
| Telegram outbox | 5 s | `notifications.tg_status`, `attempts`, `next_attempt_at`; rows claimed with SKIP LOCKED |
| Proposal expiry | 1 min | `proposed` deals past `expires_at`, moved by the state machine |
| Order expiry and the day-before notice | 5 min | `orders.status`; the notice's `dedup_key` |
| Leg reminders (FR-6.2) | 15 min | `dedup_key = reminder:<leg>:<kind>:<date>` |
| Retention purge | daily at 03:00 UTC, and at start | NULL / `deleted_at` checks on what it purges |
| Account deletion (≤ 24 h, §7) | 15 min | `users.deletion_requested_at`, `deleted_at` |
| Heartbeat | 30 s | upsert into `service_heartbeats` |
| Rate refresh (v1) | 1 h, and on demand when the snapshot is older than 15 min | `rate_quotes` by source, pair and `fetched_at` |

- **Delivery is at least once.** If the worker dies between Telegram's 200 and the
  commit, one message can go out twice; we accept that rather than lose one. A 429
  waits `retry_after`. A 403 (the user blocked the bot) sets `can_message = false`,
  and the item stays in the in-app feed.
- **Mutes and quiet hours are applied in one place**, when the outbox row is created
  or sent. Per-link mutes are MVP; quiet hours are v2.

## Consequences

- Notifications leave within about 5 s instead of the spec's minute (§9 «Потоки» 2).
  The poll is one query on a partial index, so the load is negligible.
- api's public `/healthz` reports the age of the worker's heartbeat, so one external
  check covers both processes.
- Tests call the sweeps directly (`await expire_proposals(now=…)`) against real
  Postgres. The scheduler itself is not under test.
- The backup job is not here: it runs in its own `backup` container in phase 1
  (§9), so that a stuck backup cannot hold up notifications.

## Alternatives considered

- **`pg_cron`.** It needs an extension that the official `postgres:16` image doesn't
  ship, so a custom image. SQL can't call the Bot API without `pg_net` as well, and
  the logic would split between SQL and Python, with the bot token inside the
  database.
- **APScheduler's persistent SQLAlchemy job store.** The schedule is code; persisting
  it adds pickled state and nothing else.
- **Celery with Redis.** Rejected by the spec (§8).
- **Sending from the request handler (FastAPI `BackgroundTasks`).** Lost on restart,
  and Telegram would be called from two places.
