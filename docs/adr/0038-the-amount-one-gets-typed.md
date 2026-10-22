# 0038. Each wanted currency shows what one gets, and it can be typed

Status: Accepted · Date: 2026-10-22 · Spec: FR-2.1, FR-3.1–3.5, §11; QUESTIONS L2; amends ADR-0026

## Context

Under each wanted currency the wizard shows a live preview: «Отдав 3 000 ₽ RUB, получите
≈ 36 $ USD» (ADR-0026). The api works it out, because the UI never does money
arithmetic: `POST /quote` converts an amount of the given currency into one wanted
currency, at that currency's rate (ADR-0004, ADR-0022).

The owner asked for the line to say only what one gets, and for that amount to be
editable too. Typing it in one currency changes the amount given, and with it every
other currency's amount (L2).

## Decision

**The card says what one gets.** Each wanted currency's card shows «Получите ≈ 36 $ USD»,
with the amount in a field. «≈» stays, because a market rate moves until a deal locks it
(ADR-0022).

**The api converts both ways.** `POST /quote` gains `side`:
- `"give"`, the default: `amount` is in the given currency, and the answer is in the
  wanted one, as now.
- `"want"`: `amount` is in the wanted currency, and the answer is what to give for it.

Both use the same rate (the author's, or the market's of the moment) and the same
rounding: half up, once, to cents, or to whole units with `whole`.

**The field typed last leads.**
- Typing the amount given updates every wanted currency, as now.
- Typing a wanted currency's amount asks the api what to give for it, and puts that in
  «Сумма». Every other currency follows from the new sum.
- The field being typed in keeps what the author typed. The others show the api's
  answers.
- A change to that currency's rate keeps its typed amount and works out the sum again.
  Changing its currency, removing it, or changing the given currency hands the lead back
  to the sum.
- All of it is debounced, as the preview was.

## Consequences

- The sum is rounded to cents. When the given currency is the stronger one, the amount
  the order really gives in the typed currency can be a cent of the given currency away
  from what was typed. The field shows the true amount once another field leads.
- The digest on step 2 is unchanged: it states the sum and the rates.
- An order still stores only the amount given and the rates. What one gets is never
  stored, so nothing in the database changes.

## Alternatives considered

- **Storing what one gets** (an order of «36 USD»). An order may want up to three
  currencies at moving rates. Only the amount given is the same for all of them.
- **The inverse in the browser** (`36 × 83.33`). The UI never does money arithmetic, and
  the api already holds both rates.
- **A separate endpoint for the inverse.** `POST /quote` already takes everything the
  inverse needs, and one more field says which way to go.
