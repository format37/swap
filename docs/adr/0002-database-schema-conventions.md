# 0002. Schema conventions: names, keys, statuses, money, indexes, a guarded journal

Status: Proposed · Date: 2026-10-21 · Spec: §5, §7 «Целостность», §13 row 2

## Context

§5 sketches the entities. §13 fixes money as `NUMERIC(18,2)` and statuses as ENUM or
text with CHECK, never integer codes. §7 requires every deal status change to be
journaled in the same transaction, with no direct status `UPDATE`s, and the last
migration to be reversible.

## Decision

**Names.** Tables are snake_case and plural. Primary keys are `id`, foreign keys
`<entity>_id`. Columns ending in `*_at` are `timestamptz` in UTC. Calendar dates keep
the spec's names (`available_from`, `due_date`) and are `date`. Constraint names come
from one SQLAlchemy `naming_convention` (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`), which
keeps autogenerate and downgrades deterministic.

**Keys.** Primary keys are `uuid`, generated in Python (`uuid4`), so related rows can
be built before a flush. An id reveals no volume and can't be guessed from a deep
link (`deal_<id>`). Object-level authorization is still the real fence. `telegram_id`
is `bigint`. `events.id` is a `bigint` identity, because the journal needs a total
order that timestamps can't guarantee.

**Statuses** are `text` with `CHECK (status IN (…))`, rendered from the same Python
`StrEnum` the code uses. A test compares each migrated CHECK with its enum. They are
not PG `ENUM`s, because a value added with `ALTER TYPE … ADD VALUE` cannot be dropped,
and that breaks "downgrade the last migration".

**Numbers.** Money is `numeric(18,2)` with `CHECK (amount > 0)`, `Decimal` in Python
and a string in JSON. Rates are not money and use `numeric(20,10)`: RUB→GEL ≈ 0.0339
doesn't survive two decimals. Markup is `numeric(3,1)` with a CHECK between −5 and 5.
Currency is `char(3)` and country `char(2)`, each with an upper-case CHECK. Which
currencies are allowed is configuration (FR-2.2), not schema.

**MVP tables.** Key columns only; the rest arrive migration by migration.

| Table | Notes |
|---|---|
| `users` | `telegram_id` is unique and becomes NULL on deletion; the row stays as «Удалённый участник», so closed deals keep a counterparty. Unique `lower(username)` where not null. `display_name`, `locale`, `tz`, `can_message` (the bot may write to them) |
| `sessions` | `token_hash` unique (the token is never stored), `user_id`, `expires_at`, `last_used_at` for the sliding 30 days |
| `links` | One row per pair: CHECK `user_lo_id < user_hi_id` plus a unique pair. `status` is pending / active / declined / removed / blocked, with `requested_by`, `blocked_by`, and `declined_at` for the 7-day cooldown (FR-1.2) |
| `invites` | `token_hash` unique, `created_by`, `expires_at`, `used_by`, `used_at`, `revoked_at` |
| `orders` | Spec fields with CHECKs `0 < amount_min ≤ amount_max`, `0 ≤ amount_remaining ≤ amount_max`, `available_from ≤ available_until`. `payout_methods text[]`, `rate_spec jsonb` (ADR-0004) |
| `order_wants` | Rows of `(order_id, currency, country)` instead of a JSON array, so v1 matching is an indexed join |
| `order_visibility` | PK `(order_id, user_id)`. No rows means all active links (§3) |
| `deals` | Spec fields, plus the `rate_spec` snapshot, `rate_quote_id`, `expires_at`, `cancel_requested_by`, and dispute and resolution columns. CHECK `proposer_id <> acceptor_id` |
| `deal_legs` | Unique `(deal_id, seq)`, CHECK `seq IN (1, 2)` and `payer_id <> payee_id`. `recipient_details jsonb` holds the encrypted envelope (ADR-0004) |
| `documents` | Unique `(leg_id, sha256)`, so a screenshot sent twice is stored once |
| `rate_quotes` | `source`, `base`, `quote`, `value`, `fetched_at`, and `entered_by` for manual rates |
| `events` | `deal_id` or `order_id` (CHECK exactly one), `actor_id` (NULL means the system), `type`, `payload jsonb` |
| `notifications` | One row per recipient. It is the Telegram outbox (`tg_status`, `attempts`, `next_attempt_at`, `tg_message_id`) and the in-app feed (`read_at`). A unique `dedup_key` (for example `reminder:<leg>:<kind>:<date>`) makes one-time messages idempotent. Link requests live here, not in `events` |
| `service_heartbeats` | `name`, `beat_at`. The worker writes its heartbeat here, and api's `/healthz` reads its age |

**The journal is guarded in the database.**
- `events` is append-only: a trigger rejects UPDATE and DELETE.
- Orders and deals are never hard-deleted. Account deletion closes and scrubs them
  instead, so the foreign keys from `events` can be `RESTRICT`.
- The state-machine service changes a deal in one transaction: it locks the row
  (`SELECT … FOR UPDATE`), checks the transition, updates the row, and inserts the
  event.
- A deferred constraint trigger backs this up. If a transaction changes
  `deals.status` without inserting a matching event for that deal, it fails at
  commit, so a stray `UPDATE` can't slip past review.

**Indexes.** Every foreign key is indexed, plus partial indexes for the worker's
sweeps: open orders by `available_until`, proposed deals by `expires_at`, legs not yet
received by `due_date`, pending notifications by `next_attempt_at`, and unread
notifications by `(recipient_id, created_at)`.

**Migrations.** Alembic only, never `create_all`. One revision per PR that touches the
schema, and every revision has a working `downgrade()`. CI runs
`upgrade head → downgrade -1 → upgrade head` on an empty database.

## Consequences

- Constraint names are stable, so a hand-written downgrade can always name what it
  drops.
- Adding a status is a two-line migration that drops and recreates a CHECK, and it
  can be undone.
- The balance stays a query over `deal_legs` (§5). A view can come later if volume
  ever asks for one.
- A test that sets a deal's status without the service fails at commit. That is
  intended.

## Alternatives considered

- **Serial integer ids.** Enumerable, and they leak counts; there is no benefit at
  tens of users.
- **PG `ENUM`.** Rejected above.
- **`wants` as a JSONB array** (the spec's sketch). Fine for display, awkward for
  matching.
- **Enforcing the journal only by code review.** §7 asks for an invariant, and a
  trigger is about twenty lines.
