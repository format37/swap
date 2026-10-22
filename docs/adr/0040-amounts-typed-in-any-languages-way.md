# 0040. Amount fields read every language's way of writing a number

Status: Accepted · Date: 2026-10-22 · Spec: §7 «Локализация», §11; QUESTIONS M2; amends ADR-0017

## Context

The app writes amounts with `Intl` in the user's language. Russian and Georgian write
«150 000» and «1 712,33». English, as `en-GB`, writes «150,000» and «1,712.33» (ADR-0009,
ADR-0015). Some fields are filled by the app itself: the proposal's amount (QUESTIONS G4),
and the wizard's sum after a typed «Получите» (ADR-0038). People also type in their own
habits, which need not match the app's language.

`parseAmount` dropped spaces and read the first comma as the decimal point. In English,
«2,920» became 2.920, which is no amount: the sum vanished, and the other currencies'
«You get» emptied (QUESTIONS M2). The proposal's «150,000» was refused the same way.

## Decision

An amount field takes digits with spaces (plain, no-break or narrow), commas and points.

- Money has at most two decimals. So the last comma or point is the decimal point when
  one or two digits follow it.
- Every other comma or point groups thousands, and exactly three digits must follow each.
- «150 000», «150,000» and «150.000» are 150000. «1 712,33», «1,712.33» and «1.712,33»
  are 1712.33. «1712,5» is 1712.5. «1,2345» is no amount.
- Rates keep their own reading. A rate can have ten decimals, so «0,034» stays 0.034
  (ADR-0004).

## Consequences

- Whatever the app writes into a field, in any of its languages, reads back as the same
  amount.
- «1.500» is 1500, as a German or a Russian habit has it. Nobody writes money with three
  decimals.

## Alternatives considered

- **A reader per language.** People don't always type in the app's language, and the
  app's own numbers would still have to round-trip.
- **Filling fields without grouping** («81900»). Long numbers are hard to read in the
  wizard, and an English «1,500» typed by hand would still be refused.
