# Architecture decision records

One page per decision: what we decided and why, so nobody has to ask in chat.
A decision that changes the spec goes through `docs/QUESTIONS.md` first and gets
its record once the owner has answered.

Status is one of **Proposed** (written, waiting for the owner's review),
**Accepted**, or **Superseded by NNNN**. A superseded record is kept, not edited.

| # | Decision | Status |
|---|---|---|
| [0001](0001-subdomain-and-routing.md) | `swap.latentstate.dev` at the root of its own origin; one upstream behind the shared Caddy | Accepted |
| [0002](0002-database-schema-conventions.md) | Names, keys, statuses, money, indexes; the journal guarded in the database | Accepted |
| [0003](0003-ui-primitives.md) | Own primitives on Tailwind plus Telegram-native controls; readable without reading | Accepted |
| [0004](0004-rate-spec-and-recipient-details.md) | `rate_spec` and encrypted `recipient_details` as versioned JSONB | Accepted |
| [0005](0005-background-jobs.md) | APScheduler in one worker; every job is an idempotent sweep | Accepted |
| [0006](0006-mvp-build-order.md) | MVP build order: vertical slices, link + order + deal first | Accepted |
| [0007](0007-openapi-client.md) | openapi-typescript + openapi-fetch; contract drift fails CI | Accepted |
| [0008](0008-telegram-through-the-vps-bot-api-server.md) | Telegram through the VPS's Bot API server and relay; the worker does all of it | Accepted |
| [0009](0009-languages.md) | Russian, English and Georgian from the start | Accepted |
| [0010](0010-payment-details.md) | Payment details: saved free text per asset, copied into the deal | Accepted |
| [0011](0011-phase-0-platform.md) | Phase-0 platform: sessions, router, tooling, logs, deploy | Accepted |

Rows 0001–0007 are the developer decisions of SPEC §13, one record each. The
owner accepted them on 2026-10-21; the amendments made on acceptance are in the
records themselves, which had not been accepted before. 0008–0011 come from the
owner's answers of the same day.

## Template

Copy to `NNNN-short-title.md` with the next free number.

```markdown
# NNNN. Title in a sentence

Status: Proposed · Date: YYYY-MM-DD · Spec: §x

## Context
## Decision
## Consequences
## Alternatives considered
```
