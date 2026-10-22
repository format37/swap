# 0036. Recurring orders: a monthly copy on day N, published once

Status: Accepted · Date: 2026-10-22 · Spec: §12 v2; QUESTIONS K7; ADR-0005, ADR-0034

## Context

The owner asked for «Флаг создать авто заявку каждого N числа» (K7). §12 had recurring
orders in v2 («каждый месяц с 5-го»), and the owner pulled them forward. The details
came with the list: a copy on day N, or the last day of a shorter month, with a new
number; a fixed rate stays fixed and the market's follows the market; «Больше не
повторять» on any copy ends the series; and the job is idempotent (ADR-0005).

## Decision

**A series** is the orders that share `series_id`, the first order's id. Each one says
which month it is for (`series_month`). The database allows one order per series and
month. `repeat_day`, 1–31, sits on every order of the series while it repeats.

**The first order stands for its own month.** Copies start the month after it, so
publishing on the 3rd with N = 5 doesn't make a copy two days later.

**The sweep**, every ten minutes in the worker (`swap/repeats.py`):
- it takes the latest order of each repeating series as its template;
- once the author's own calendar reaches day N of a month the series has no order for
  (the month's last day, if it is shorter), it publishes a copy through the same code as
  the wizard.

The copy gets a new number (ADR-0034), today as its first day, and the template's window
if it had one. Amounts, ways, each currency's rate spec, the reach and the note stay as
they were. It is announced like any new order. At reach 0, the list keeps only people
still linked, and with nobody left that month goes by.

**Idempotent.** The unique series-and-month pair makes a second run, or one racing it,
publish nothing more. A missed month isn't made up: only the current one is due.

**Stopping.** «Больше не повторять» on any order of the series clears `repeat_day` on all
of them (`POST /orders/{id}/stop-repeating`). Deleting the account stops its series too.
Closing or deleting a copy doesn't: the next month's copy still comes, and the card says
the order repeats.

## Consequences

- Last month's copy stays as it is: the author closes it, or deals use it up.
- The wizard asks for N among the dates, and step 2's digest says «каждый месяц, 5-го».

## Alternatives considered

- **A table of series.** The orders already carry everything a copy needs, and the latest
  one is the template.
- **Making up missed months.** Two orders published at once after a pause would be noise.
