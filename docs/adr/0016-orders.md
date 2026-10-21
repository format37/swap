# 0016. Orders: four statuses, one set of payment kinds, visibility as one predicate

Status: Accepted · Date: 2026-10-22 · Spec: §3, §5, FR-2.1–2.6, FR-3.1, FR-7.1; Q-B5, Q-B17, Q-E2; ADR-0002, ADR-0004

## Context

The spec's `Order` has the statuses draft, open, partially_matched, fulfilled, cancelled
and expired. It also has payout methods from a fixed list, and visibility for all links or
chosen ones. ADR-0002 fixed the tables, and ADR-0004 fixed `rate_spec` and the formula.
Q-B17 dropped server drafts and made dates calendar dates in the author's time zone.
The owner added crypto to the payout methods. Kickoff rule 6 makes visibility the first
thing tested.

## Decision

**Statuses: open, fulfilled, closed, expired.**
- There is no `draft`: the wizard keeps its state until «Опубликовать» (Q-B17).
- There is no `partially_matched`: «частично» reads from the remainder and the maximum,
  and a status of its own would only need keeping in step.
- `closed` replaces `cancelled`. The author closes what remains (FR-2.5), and accepted
  deals carry on, so nothing was cancelled.
- `fulfilled` is set once the remainder falls below the smallest deal (Q-B5). It returns
  to `open` when a cancelled deal brings the remainder back up (FR-2.3). That arrives
  with deals.

**One set of payment kinds.** An order's payout methods and the kinds of saved payment
details (ADR-0010) are the same six: card, phone (a transfer to a phone number, such as
SBP), bank, crypto, cash and other. A CHECK keeps `payout_methods` a non-empty subset.

**Visibility is one predicate**, `seen_by(viewer)` in `swap/orders.py`, used by every
query that reads orders. The author always sees their own. Anyone else sees an order when
all of these hold:
- it is `open`, and its last day hasn't passed in the author's time zone (until slice 5's
  sweep marks it expired);
- the viewer and the author are actively linked (§3; not transitively);
- the order has no list, or the viewer is on it.

An order the viewer may not see answers 404, as one that doesn't exist. The list may hold
only people actively linked to the author when it is published. An order for all links
also reaches links made later; one for chosen people never does. Who is on the list is
told to the author alone.

**Publishing tells everyone who can see it** (FR-7.1, `order.opened`): the author's
active links, or the people on the list. Links made later are not told.

**Dates** are calendar dates. The last day may not have passed in the author's time zone
when the order is published. The app sends the device's zone at the first launch
(`PATCH /me`). The server checks it against its zone data, and an author without one
counts in UTC.

**Rates.** Only `fixed` in slice 1: one quote per wanted currency, between it and the
given currency, and none for anything else (ADR-0004). The manual rate arrives in slice 6.
The formula lives in `swap/rates.py`. Previews come from `POST /api/v1/quote`, which is
stateless, so the wizard can ask before an order exists.

**Assets** are config (FR-2.2): `ASSETS`, by default RUB, GEL, USD, EUR, TRY, KZT, AMD,
USDT and USDC. A country is any two capital letters. The app offers a short list.

**Money crosses the api as decimal strings** matched by a pattern. A JSON number is
refused, and so are "1e3" and amounts with more than two decimals (ADR-0007).

## Consequences

- A visibility bug has one place to live, and the negative tests exercise that place
  through every endpoint.
- «Частично исполнена» is a display rule, and every status in the table is a decision
  someone made.
- Pending proposals on an order that closes are cancelled in the same transaction
  (Q-E2). That arrives with deals, which own the proposals.

## Alternatives considered

- **Row-level security in Postgres.** The rule would move into SQL policies with a
  session variable per request. That is more machinery than one predicate needs at this
  scale, and harder to read in review.
- **Notifying links made after publication.** It would need a sweep over orders per new
  link, and an old order would surface as news.
- **ISO country validation on the server.** It would need a 249-entry list in Python. The
  app's picker only offers real codes, and a typo harms nobody.
