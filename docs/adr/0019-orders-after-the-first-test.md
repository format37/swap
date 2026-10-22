# 0019. Orders after the first test: no minimum or last day needed, ways to be paid, reopen and delete

Status: Accepted · Date: 2026-10-22 · Spec: FR-2.1, FR-2.3, FR-2.5, FR-2.6; QUESTIONS F1–F4, F6, F7; amends ADR-0016

## Context

The owner tried slice 1 on his own and asked for less to fill in and more control over
old orders (QUESTIONS part F). ADR-0016 had a positive minimum, a required last day,
payment ways for the author's side only, and `closed` as the end.

## Decision

**No minimum** (F4). `amount_min` may be 0, and the wizard sends 0 for an empty field.
A deal still takes at least a cent, so the smallest deal is `max(amount_min, 0.01)`
(`swap.orders.smallest_deal`). The order is fulfilled once the remainder falls below it
(Q-B5): with a minimum of 0, once nothing remains.

**No last day** (F3). `available_until` is nullable, and NULL means open until the
author closes it. Visibility counts it as never passed. The wizard's «Ограничить срок»
is off by default; turning it on suggests two weeks, as Q-B17 did. Slice 5's expiry
sweep and FR-2.6's day-ahead warning pass such orders by.

**Ways to be paid** (F2). `orders.receive_methods` holds the same six kinds as
`payout_methods`, under the same CHECK. There is one set per order, not per wanted
currency, because an order rarely wants more than one. A proposal's `counter_method`
must be in it (422 `deal.method_not_accepted`). Orders published before it get all six,
which is what a proposal could choose until then.

**Reopen** (F7). The author can reopen a `closed` order. It is `open` again, with its
remainder, list and dates as they were, provided its last day hasn't passed (409
`order.window_past`). Nobody is told again, and the proposals cancelled at closing
(Q-E2) stay cancelled. Fulfilled and expired orders don't reopen: one has nothing left,
and the other needs a new date, which is order editing (slice 2).

**Delete** (F6). The author can delete an order that isn't open: `orders.deleted_at` is
set, and the order leaves every list and card, the author's own included. It answers 404,
like one that never existed. The row stays, because its deals point at it; account
deletion scrubs it with the rest (Q-B10). An open order is closed first, so its
proposals are cancelled by the one path that does that (Q-E2).

**Wording** (F1). Each currency list opens with the side it is for, «Отдаёте» or
«Получаете». While a list covers the screen, its field's label can't be seen.

## Consequences

- `seen_by` gains two conditions: a NULL last day hasn't passed, and a deleted order is
  nobody's.
- A minimum of 0 goes unsaid on the card, and the proposal's range reads «до …».
- A closed order still gets its amount back when an accepted deal is cancelled (FR-2.3),
  so a reopened one has the remainder it should.

## Alternatives considered

- **Archive instead of delete.** It would hide orders from «Мои» and keep a list to
  restore them from. With reopening on the closed card, that list would be one more
  place for the same orders. The owner offered either, and delete is the smaller one.
- **Deleting the row.** Deals and their journal point at the order. Deleting rows when
  there are none and hiding them otherwise would be two paths for one action.
- **Ways to be paid per wanted currency.** It is more exact for an order that wants GEL
  in cash and USD by bank, but it means a list per currency for a case nobody has had.
- **A NULL minimum.** The column stays NOT NULL, and 0 says what it means.
