# 0022. An order follows the market unless its author fixes the rate

Status: Accepted · Date: 2026-10-22 · Spec: FR-3.2–3.6, §11; QUESTIONS G2, Q-B3; ADR-0004, ADR-0020

## Context

PR 1.10 filled the wizard's rate in from Coinbase, but it still published a fixed rate:
the number of that minute, for weeks. The owner asked for the opposite default (G2). An
order should hang at the market's rate, pulled from the API whenever someone looks at
it, unless its author fixed the rate on creating it.

ADR-0004 already reserved `{"type": "reference", …}` in `rate_spec`, with source and
markup for v1. Q-B3 locks every rate at the proposal in the MVP.

## Decision

**`rate_spec` is fixed or reference.**
- `{"v": 1, "type": "reference", "source": "coinbase"}` is the default the wizard
  sends.
- The author's own numbers remain `type: "fixed"`, behind «Зафиксировать курс» on step
  2, prefilled from the market as before.
- Pydantic tells the two apart by `type`. The database CHECK allowed both already.
- No markup yet. It can join with a default of 0.

**Whoever looks sees the rate of the moment.**
- The order card asks `GET /api/v1/rates/market` for each wanted currency, and shows
  «Курс по рынку: 1 GEL = 31,27 RUB · Coinbase, 14:02».
- `POST /api/v1/quote` takes either kind of spec, and returns the rate it used beside
  the amount, so the proposal can show it.

**A proposal locks it** (Q-B3, FR-3.5).
- `swap.market.lock` turns a reference spec into the market's rate of that moment,
  read «1 strong = so many weak» (the side that makes it at least 1).
- The deal stores it as a fixed spec of one quote, so nothing about the deal moves with
  the market. Two new columns record where and when: `deals.rate_source` and
  `rate_fetched_at`.
- The deal card says «по рынку Coinbase, 14:02» after the rate.
- Without a market rate, which happens when Coinbase has been away for a day (ADR-0020),
  there is no proposal: 503 `rate.unavailable`.

## Consequences

- Two people looking at the same order a minute apart may see different counter-amounts.
  That is what the owner asked for, and the proposal shows the one it will lock.
- The acceptor accepts the rate the proposal locked, not the rate of the moment they
  accept. A proposal lasts 48 hours, so the market may have moved by then. Locking at
  acceptance (FR-3.4) is v1's choice.
- Deals keep working without Coinbase, because each stores its own copy.

## Alternatives considered

- **Locking at acceptance.** It is fairer to the author when the market moves, but the
  proposer would then send a proposal without knowing its amounts. It stays FR-3.4's
  option for v1.
- **Snapshotting the rate into the order at publication.** That is the fixed rate the
  owner didn't want.
- **Recomputing open proposals as the market moves.** Amounts that change after both
  sides have looked at them are worse than a rate that is a little old.
