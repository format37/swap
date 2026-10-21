# Architecture decision records

One page per decision: what we decided and why, so nobody has to ask in chat.
A decision that changes the spec goes through `docs/QUESTIONS.md` first and gets
its record once the owner has answered.

Status is one of **Proposed** (written, waiting for the owner's review),
**Accepted**, or **Superseded by NNNN**. A superseded record is kept, not edited.

| # | Decision | Status |
|---|---|---|
| [0001](0001-subdomain-and-routing.md) | `swap.latentstate.dev` at the root of its own origin; one upstream behind the shared Caddy | Proposed |
| [0002](0002-database-schema-conventions.md) | Names, keys, statuses, money, indexes; the journal guarded in the database | Proposed |
| [0003](0003-ui-primitives.md) | Own primitives on Tailwind plus Telegram-native controls; no component library | Proposed |
| [0004](0004-rate-spec-and-recipient-details.md) | `rate_spec` and encrypted `recipient_details` as versioned JSONB | Proposed |
| [0005](0005-background-jobs.md) | APScheduler in a singleton worker; every job is an idempotent sweep | Proposed |
| [0006](0006-mvp-build-order.md) | MVP build order: vertical slices, link + order + deal first | Proposed |
| [0007](0007-openapi-client.md) | openapi-typescript + openapi-fetch + openapi-react-query; contract drift fails CI | Proposed |

Rows 0001–0007 are the developer decisions of SPEC §13, one record each.

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
