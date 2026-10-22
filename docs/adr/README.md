# Architecture decision records

One page per decision: what we decided and why, so nobody has to ask in chat.
A decision that changes the spec goes through `docs/QUESTIONS.md` first and gets
its record once the owner has answered.

Status is one of **Proposed** (written, waiting for the owner's review),
**Accepted**, or **Superseded by NNNN**. A superseded record is kept, not edited.

| # | Decision | Status |
|---|---|---|
| [0001](0001-subdomain-and-routing.md) | `swap.latentstate.dev` at the root of its own origin; one upstream behind the shared Caddy | Accepted |
| [0002](0002-database-schema-conventions.md) | Names, keys, statuses, money, indexes; the journal guarded in the database | Accepted; journal guard amended by 0018, erasing a deal by 0030 |
| [0003](0003-ui-primitives.md) | Own primitives on Tailwind plus Telegram-native controls; readable without reading | Accepted; photos amended by 0027 |
| [0004](0004-rate-spec-and-recipient-details.md) | `rate_spec` and encrypted `recipient_details` as versioned JSONB | Accepted; details superseded by 0021; a spec per wanted currency by 0026 |
| [0005](0005-background-jobs.md) | APScheduler in one worker; every job is an idempotent sweep | Accepted |
| [0006](0006-mvp-build-order.md) | MVP build order: vertical slices, link + order + deal first | Accepted |
| [0007](0007-openapi-client.md) | openapi-typescript + openapi-fetch; contract drift fails CI | Accepted; forms amended by 0017 |
| [0008](0008-telegram-through-the-vps-bot-api-server.md) | Telegram through the VPS's Bot API server and relay; the worker does all of it | Accepted |
| [0009](0009-languages.md) | Russian, English and Georgian from the start | Accepted; formats amended by 0015 |
| [0010](0010-payment-details.md) | Payment details: saved free text per asset, copied into the deal | Superseded by 0021 |
| [0011](0011-phase-0-platform.md) | Phase-0 platform: sessions, router, tooling, logs, deploy | Accepted |
| [0012](0012-links-and-invites.md) | Links: one pending request, whether it came by invite or by @username | Accepted |
| [0013](0013-deep-links.md) | Deep links: the bot's buttons open `startapp=<kind>_<id>` | Accepted |
| [0014](0014-notifications-outbox.md) | Notifications: an outbox row per recipient, worded and sent by the worker | Accepted |
| [0015](0015-georgian-without-intl-data.md) | Georgian numbers and dates borrow Russian's rules; Georgian dates stay numeric | Accepted |
| [0016](0016-orders.md) | Orders: four statuses, one set of payment kinds, visibility as one predicate | Accepted; amended by 0019, 0021, 0023, 0026 and 0028 |
| [0017](0017-forms-without-a-form-library.md) | Forms keep state in React and rules in one pure module; no react-hook-form or zod | Accepted |
| [0018](0018-deals.md) | Deals: one state machine, two legs, a journal guard that fires at once | Accepted; legs amended by 0024 |
| [0019](0019-orders-after-the-first-test.md) | Orders after the first test: no minimum or last day needed, ways to be paid, reopen and delete | Accepted; deleting amended by 0030 |
| [0020](0020-market-rate-from-coinbase.md) | The wizard's rate starts at the market's: Coinbase's public rates | Accepted |
| [0021](0021-deals-plan-the-exchange-only.md) | Deals plan the exchange only: no payment details, three ways to pay | Accepted |
| [0022](0022-market-rate-by-default.md) | An order follows the market unless its author fixes the rate | Accepted; per wanted currency since 0026 |
| [0023](0023-an-orders-history.md) | An order's history stays open to whoever dealt on it | Accepted; amended by 0028 and 0030 |
| [0024](0024-both-legs-at-once.md) | A deal's two transfers run at once, with no order and no dates | Accepted |
| [0025](0025-error-reports-to-sentry.md) | Errors go to one Sentry project, with nothing personal in them | Accepted |
| [0026](0026-two-step-wizard-and-a-rate-per-currency.md) | The wizard in two steps, and a rate for each wanted currency | Accepted |
| [0027](0027-people-with-photo-name-and-username.md) | People are shown with their Telegram photo, name and @username | Accepted |
| [0028](0028-reach-by-handshakes.md) | An order reaches as far along chains of links as its author says | Accepted |
| [0029](0029-the-score.md) | A person's score: how many different people they settled a deal with | Accepted |
| [0030](0030-deleting-for-oneself.md) | Each side deletes for themselves, and the server erases what all have deleted | Accepted |
| [0031](0031-notification-settings.md) | Notification settings: switches on the person, mutes per pair, the outbox obeys | Accepted |
| [0032](0032-deleting-history-and-the-account.md) | Deleting all history at once, and the account | Accepted |
| [0033](0033-agreement-and-privacy-page.md) | The agreement at first launch, and a public privacy page | Accepted |
| [0034](0034-order-numbers.md) | Every order has a number, «№ 17», from one sequence | Accepted |
| [0035](0035-csv-export-through-the-bot.md) | The CSV export arrives as a file from the bot | Accepted |
| [0036](0036-recurring-orders.md) | Recurring orders: a monthly copy on day N, published once | Accepted |
| [0037](0037-ways-to-be-paid-per-currency.md) | Each wanted currency has its own ways to be paid | Accepted |
| [0038](0038-the-amount-one-gets-typed.md) | Each wanted currency shows what one gets, and it can be typed | Accepted |
| [0039](0039-a-settings-tab-and-the-language-telegram-has.md) | A settings tab, and the language Telegram has | Accepted |
| [0040](0040-amounts-typed-in-any-languages-way.md) | Amount fields read every language's way of writing a number | Accepted |

Rows 0001–0007 are the developer decisions of SPEC §13, one record each. The
owner accepted them on 2026-10-21; the amendments made on acceptance are in the
records themselves, which had not been accepted before. 0008–0011 come from the
owner's answers of the same day.

0012 onwards are decisions made while building phase 1, under the owner's
delegation ("feel free to decide"). The owner reviews them after the fact. 0026–0030
record the owner's notes of QUESTIONS part J, and 0037–0039 those of part L: the
decisions are the owner's, and the details and defaults are mine.

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
