# 0037. Each wanted currency has its own ways to be paid

Status: Accepted · Date: 2026-10-22 · Spec: FR-2.1, FR-4.1; QUESTIONS L1; amends ADR-0019 and ADR-0026

## Context

ADR-0019 gave an order one set of ways to be paid, `orders.receive_methods`, under the
same CHECK as `payout_methods`. It weighed a set per wanted currency and left it out,
"for a case nobody has had". ADR-0026 put that one «Как получать» at the end of the
«Получаете» group, under all the wanted currencies.

The owner now has the case. He takes GEL in cash or by bank, and USD only by bank (L1).
With one set, an order that lists both currencies offers cash for USD too.

## Decision

**The ways belong to the wanted currency.**
- `order_wants.receive_methods` holds the same six kinds, under the same CHECK as the
  order's columns: not empty, each kind once at most.
- `orders.receive_methods` goes.
- Migration 0024 copies each order's set into every one of its wanted currencies. Its
  downgrade puts back, on each order, every kind any of its currencies had.

**The api.**
- `OrderDraft.wants[]` and `Order.wants[]` each carry `receive_methods`, and the
  order-level field goes. A currency with no way is refused with a 422, as an order
  without ways was.
- A proposal's `counter_method` must be one of the ways of the currency it picks,
  `want_currency`. Otherwise it gets 422 `deal.method_not_accepted`, as before.
- The contract changes shape, so the generated client is regenerated (ADR-0007).

**The wizard.**
- Each wanted currency's card ends with its own «Как получать».
- The first currency starts with none chosen, as the order's set did. «Ещё валюта»
  starts the new currency with the ways of the one above it, so an order whose
  currencies share their ways costs no extra taps.
- The step's check names the currency that still has no way.

**Elsewhere.**
- The order's card lists each currency's ways on that currency's line.
- The proposal offers the ways of the currency it picks, and picking another currency
  changes the offer.
- A recurring order's copy (ADR-0036) copies each currency's ways.

## Consequences

- Orders published before this keep their old set for every currency, which is what
  they offered until now.
- The bot's messages don't list the ways, so they don't change.
- A deal already stores the way it uses in its legs, so deals don't change.

## Alternatives considered

- **One set per order, with exceptions per currency.** It saves nothing over a set per
  currency, and it is harder to read.
- **A map on the order** (`{"GEL": ["cash", "bank"], "USD": ["bank"]}`). Each wanted
  currency is already a row, with its own rate (ADR-0026), and its ways belong beside it.
