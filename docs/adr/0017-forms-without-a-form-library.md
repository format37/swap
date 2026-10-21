# 0017. Forms keep their state in React and their rules in one pure module, without react-hook-form or zod

Status: Accepted · Date: 2026-10-22 · Spec: §8 «Формы»; amends the zod point of ADR-0007

## Context

§8 names react-hook-form and zod for the order wizard and the proposal. ADR-0007 adds
that zod schemas describe what a person types, mapped into the generated request types at
submit. Building the wizard showed what its form actually holds:
- a handful of native selects, two amount fields, chips and dates;
- a list of wanted currencies, each with its own rate;
- three steps behind Telegram's MainButton, not an HTML submit.

Its rules are a dozen lines: amounts and rates must parse, the least deal can't exceed the
total, the dates must be in order, and a currency can't be wanted twice. The owner asked
for no overengineering.

## Decision

- **A form's state is one `useState` of strings, as typed.** That covers commas, spaces
  and «1 712,50».
- **Its rules live in one pure module per form**, such as `src/orders/form.ts`. A function
  per step says what is wrong as a dictionary key, or nothing. `toDraft()` turns a valid
  form into the generated request type, so the compiler checks the mapping that ADR-0007
  gives to zod.
- **Those modules are unit-tested** without React. A screen test walks the steps once and
  checks the exact body sent.
- **Amounts and rates are parsed as text**, into the api's decimal strings. Comparisons
  run in cents as `bigint`, so there is no float on the way (ADR-0004).
- **A problem is shown when the main action is pressed**, under the step. A disabled
  MainButton gives no reason.
- If a later form outgrows this, with many fields and cross-field rules, zod comes in for
  that form, with an amendment to this record.

## Consequences

- Nothing is added to the bundle. react-hook-form and zod together would cost about
  20 KB gzip.
- A form's validation reads as plain code, and its tests need no form harness.
- The proposal (PR 1.7) follows the same pattern.

## Alternatives considered

- **react-hook-form with zod**, as §8 names them. Registration and resolvers for fields
  that are mostly native selects and chips; MainButton isn't a form submit, so its
  ergonomics barely apply.
- **zod alone**, for the rules. A schema per step does the same job as the step
  functions, plus a library and a second way of writing types.
