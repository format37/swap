# 0020. The wizard's rate starts at the market's: Coinbase's public rates

Status: Accepted · Date: 2026-10-22 · Spec: FR-3.1, FR-3.3, FR-3.6, §11; QUESTIONS F5, Q-C1; ADR-0004

## Context

The owner asked for the wizard to propose a rate at once, from an exchange outside Russia
with a free API, any popular one (F5). Until now the author typed every rate. The spec
plans live sources for v1 (FR-3.3: NBG and CBR), and Q-C1 proposed CBR for the rouble.
The owner's words rule CBR out.

Who has every asset Swap trades (RUB, GEL, USD, EUR, TRY, KZT, AMD, USDT, USDC), for
free, with no key? I checked on 2026-10-22:
- **Coinbase**, `api.coinbase.com/v2/exchange-rates`: all nine, as decimal strings,
  without a key, and a US exchange. 1 GEL = 31,40 RUB.
- **NBG**: an official rate, not an exchange's, and only against GEL. 1 GEL = 31,66 RUB.
- **ExchangeRate-API's open endpoint**: an aggregator with daily rates, sent as JSON
  numbers. 1 GEL = 31,63 RUB.
- **Binance** trades no RUB or GEL pair any more, though its ticker still answers
  USDTRUB with a frozen 91,10. **Frankfurter** (ECB) lists neither RUB nor GEL.

## Decision

**Coinbase's public table is the source**, with USD as the base: `GET
https://api.coinbase.com/v2/exchange-rates?currency=USD`. One answer covers every pair,
cross through USD where neither side is USD (FR-3.3 does the same). Its rates are parsed
as `Decimal` from their strings, and anything that isn't a positive decimal string is
left out (`swap/market.py`).

**The api asks, not the app.** `GET /api/v1/rates/market?base=GEL&quote=RUB` returns the
rate, rounded the way people type one, with its source and time:
- Rounding goes to the cent from 1 up, and to four significant figures below 1:
  «31,40», «0,03185».
- The answer is kept for ten minutes, so Coinbase hears from Swap at most six times an
  hour.
- While Coinbase can't be reached, the last answer serves for a day, with its time
  (FR-3.6). After that the endpoint answers 503 `rate.unavailable`, and the author types
  the rate as before.
- The app loads nothing from a third party, so the kickoff's rule holds.

**It is a suggestion.** The wizard fills each untouched rate with it, and refills it when
the pair or its direction changes. What the author types stays. A line under the rate
says «Курс Coinbase, 12:00», and adds the market's rate once the author's differs.
Tapping the line puts it back. The order stores a fixed rate, as before (ADR-0004), so
no deal depends on Coinbase, and nothing is stored about it.

## Consequences

- `httpx` becomes a runtime dependency of the api. It makes the only call the api makes
  outside, with a 5-second timeout.
- The tests use a recorded table through `httpx.MockTransport`, so CI never calls out.
- This answers Q-C1 for the MVP. The rates v1 will lock at proposal or acceptance
  (FR-3.4) can come from the same `Market`, and NBG can join as a second source if
  someone asks for the official rate.

## Alternatives considered

- **NBG**: official, free and Georgian. But it is a central bank, not an exchange, and
  it quotes only against GEL.
- **ExchangeRate-API or fawazahmed0's currency API**: both free and both broad. But
  they are aggregators updated once a day, not exchanges, and the first sends floats.
- **A worker job filling a `rate_quotes` table**: the spec's RateQuote. It would be a
  table, a job and a migration for a number that is only a suggestion. That table comes
  with rates that deals lock (v1).
- **Calling Coinbase from the app**: fewer moving parts. But it would mean a third
  party in the frontend's CSP, and every phone asking.
