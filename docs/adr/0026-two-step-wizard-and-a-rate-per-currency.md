# 0026. The wizard in two steps, and a rate for each wanted currency

Status: Accepted · Date: 2026-10-22 · Spec: FR-2.1, FR-3.1–3.5, §11; QUESTIONS J1; amends ADR-0004, ADR-0016 and ADR-0022

## Context

The order wizard has three steps:
1. «Отдаю»: the currency and country, the amount with «Только целиком» and the minimum,
   the ways to pay out, and the dates. Each part has a section title of its own.
2. «Хочу»: up to three wanted currencies, each with its country, rate and live preview.
   Then one «Зафиксировать курс» for the whole order, and the ways to be paid.
3. «Кому видно» and the comment.

The rate belongs to the order. `orders.rate_spec` is either fixed, with a quote for every
wanted currency (ADR-0004), or the market's for all of them (ADR-0022).

The owner asked for two steps, with «Отдаёте» and «Получаете» together on the first, and
for «Зафиксировать курс» per wanted currency, off by default (J1). An order may then
fix GEL at 29,20 and leave USD to the market. One spec per order can't say that.

## Decision

**Two steps.**
- **Step 1** has two groups, «Отдаёте» and «Получаете». There are no section titles inside
  them; each row keeps its own label.
  - «Отдаёте»: currency, country, amount, «Только целиком», «Минимум за сделку», «Как вы
    можете отдать», «Когда», «Ограничить срок».
  - «Получаете»: each currency with its country, its rate, its own «Зафиксировать курс»
    and its live preview; «Ещё валюта», up to three; «Как получать».
- **Step 2** opens with a digest of step 1: «Отдаёте 150 000 RUB · Россия → GEL по рынку
  или USD по 1 USD = 80 RUB». Then come «Кому видно» and the comment.
- The main button checks the step it is on, and what stops it shows above the button
  (G5).
- The country stays, prefilled from the currency.

**A rate per wanted currency.** `order_wants.rate_spec` holds that currency's own spec,
with the shapes ADR-0004 and ADR-0022 defined:
- the market's: `{"v": 1, "type": "reference", "source": "coinbase"}`, the default;
- the author's: `{"v": 1, "type": "fixed", "quotes": [one quote]}`, between the given
  currency and this one, in either direction.

`orders.rate_spec` goes. Migration 0015 copies each order's spec into its rows: a
reference spec as it is, and a fixed one as the quote for that row's currency. Its
downgrade puts back a fixed spec when every row is fixed, and the market's otherwise.

**A currency appears once in an order.** The api refuses a repeat, as the wizard always
did. A proposal names its `want_currency`, and that has to name one rate.

**The api.**
- `OrderDraft.wants[]` and `Order.wants[]` each carry `rate_spec`, and the order-level
  field goes.
- `POST /quote` and `market.lock` already take one currency's spec. A proposal locks
  the chosen currency's own spec, as ADR-0022 describes.
- The contract changes shape, so the generated client is regenerated (ADR-0007).

**Default:** the live preview «Отдав …, получите ≈ …» stays under each wanted currency.

## Consequences

- An order can mix rates. The card shows each currency's own line: the author's fixed
  rate, or «Курс по рынку» with the source and time.
- A deal still stores one fixed quote, locked at the proposal, so deals don't change.
- Step 1 is long on a phone, and the main button stays at the bottom. The digest on
  step 2 shows everything that step 1 decided before publishing.

## Alternatives considered

- **One spec with a map inside** (`{"type": "mixed", "rates": {"GEL": …}}`). It keeps
  one column, but every wanted currency is already a row, and the rate belongs there.
- **Keeping three steps.** The owner asked for two.
- **A repeated currency in two countries,** such as GEL in Georgia and in Turkey, each
  with its own rate. Nobody has needed it, and the proposal would have to name the
  country too.
