# 0018. Deals: one state machine, two legs, and a journal guard that fires at once

Status: Accepted · Date: 2026-10-22 · Spec: §5, FR-2.3, FR-4.1–4.7, §7 «Целостность»; Q-B1, Q-B4, Q-B5, Q-B8, Q-B9, Q-E2; ADR-0002, ADR-0004, ADR-0010; amends ADR-0002's deferred trigger

## Context

Q-B1 fixed the table of states and transitions, and kickoff rule 6 requires a test for
every transition and every illegal one. ADR-0002 put the journal in `events` and backed
the rule "no status change without its event" with a deferred constraint trigger.
ADR-0010 has a deal copy the payee's chosen payment details. Q-E2 and Q-B9 cancel
proposals that someone's action leaves without a footing.

Building it showed that a deferred trigger checks nothing in the test suite. Every test
runs inside a transaction that is rolled back, and the code under test commits only
savepoints, so a deferred check never reaches its moment.

## Decision

**One module moves deals.** `swap/deals.py` holds an action per transition of Q-B1.
Each locks the deal (`FOR UPDATE`), checks the state and the actor's side, applies the
action, and journals it in the same transaction:
- someone outside the deal gets 404 for everything, as for a deal that doesn't exist;
- a wrong state is 409 `deal.invalid_transition`;
- the other side's move is 403 `deal.not_your_move`.

`swap/journal.py` is the only code that sets a status.

**The guard fires at once.** The journal writes the event first, then sets the deal's
status and points `deals.last_event_id` at that event. A `BEFORE UPDATE` trigger refuses
a status change unless `last_event_id` changed too and names an event of this deal whose
payload goes from the old status to the new one. A `BEFORE INSERT` check makes every deal
start as `proposed`. A stray `UPDATE deals SET status` fails immediately, in tests as in
production. `events` refuses UPDATE, DELETE and TRUNCATE.

**Legs.** The proposer chooses everything in the proposal: an amount in the order's own
currency, between its minimum and its remainder (Q-B5); a wanted currency; and who sends
first, the proposer by default (Q-B16). Then:
- **The author's leg** pays in the order's currency by one of its payout ways, to the
  proposer's saved details for that currency. Cash needs none.
- **The proposer's leg** pays the counter-amount by the way the proposer names, as in
  «в ответ GEL наличными». The author chooses where to receive it when accepting; cash
  needs nothing.
- The counter-amount comes from `swap/rates.py`, rounded to whole units if asked (Q-B4).
  The deal keeps its own copy of the rate spec, the quote used, and when it was locked
  (FR-3.5).

**Payment details in a leg** are a copy, sealed for that leg's row (ADR-0004).
Deleting the saved entry changes no deal. Q-B8 is enforced in one function: the payee
always reads their own, the payer once the deal was accepted, anyone else the mask.

**Remainders** (FR-2.3):
- accepting takes the deal's amount from the order, and an order left below its minimum
  becomes `fulfilled`;
- an accepted deal that ends cancelled gives its amount back, and a fulfilled order with
  enough again reopens.

**Proposals without a footing** are cancelled in the same transaction, with the reason
journaled (`swap/proposals.py`):
- when the order closes;
- when an accepted deal leaves too little for them (Q-E2);
- when the pair's link breaks (Q-B9), quietly, as breaks are (ADR-0012).

**The cancel request and the dispute** are complete in the state machine now. Their screens
and messages come with slice 4. A dispute closes when one side proposes how it ended and
the other confirms the same outcome.

**Expiry** is the one timed transition. `expire_due()` is written and tested; the sweep that
calls it every minute arrives with slice 5.

**Words.** The Russian for the two marks is «Отправлено» and «Получено», not the spec's
«Отправил» and «Получил», which are masculine. Bot messages avoid gendered verbs the same
way: «Сделка принята — Nino B (@nino).»

## Consequences

- 117 parametrized tests try each of 13 actions from each of 9 states, and check that a
  refusal leaves the deal and its journal untouched.
- The order's remainder and the deal's status change in one transaction, so no failure
  leaves them disagreeing.
- `last_event_id` is a plain column, not a foreign key. The trigger checks the reference,
  and a foreign key back to `events` would make the two tables depend on each other.

## Alternatives considered

- **The deferred constraint trigger** (ADR-0002's sketch). Correct in production, but it
  would only run in tests that commit for real, so a regression in the rule could pass CI.
- **Reserving the remainder at the proposal.** FR-2.3 reserves at acceptance. Proposals
  reserving would block an order on unanswered proposals for 48 h.
- **Strict matching of the counter-leg's way to the author's details** (card to card).
  Between a card and a bank account the payer can usually manage, and a mismatch shows on
  the card before anything is sent.
