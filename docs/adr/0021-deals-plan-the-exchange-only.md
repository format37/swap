# 0021. Deals plan the exchange only: no payment details, three ways to pay

Status: Accepted · Date: 2026-10-22 · Spec: FR-4.1, §5 DealLeg, §11; QUESTIONS G1, G3, G4, G5, G7; supersedes ADR-0010, amends ADR-0004 and ADR-0016

## Context

The demo with others stalled at the proposal (G5):
- The proposal required the proposer's saved payment details for any way but cash, and
  accepting required the author's.
- The form for adding them offered every currency and every way, and required a name
  and a text. People saved details in AMD and EUR for an order in RUB.
- No proposal was ever sent.

The owner's verdict (G3): the app plans the exchange — which currency for which, how
much, by when, and whether in cash, by bank or in crypto. The parties settle the rest
themselves.

## Decision

**No payment details in deals.**
- A proposal has:
  - the amount: all that remains, by default (G4);
  - the other currency;
  - how each side pays, from the order's ways;
  - who goes first, and the dates;
  - an optional comment (`deals.note`, up to 500 characters) for the rest, such as
    which bank.
- Accepting is one confirmation.
- Migration 0010 drops `deal_legs.recipient_title` and `recipient_details`. No
  production deal had any.
- The profile loses «Реквизиты», and so do the app's screens for them.
- The `payment_methods` table, its api and `RECIPIENT_KEYS` stay until the owner
  answers G7: four entries live there, and deleting them can't be undone.

**Three ways: cash, bank, crypto** (PR 1.13).
- A card, a phone transfer (SBP) and «other» all move money between accounts, which is
  «bank».
- A migration maps them in orders, deals and the stored entries. The CHECKs then allow
  the three.

**What stops a form stays in sight** (G5).
- On the wizard, the proposal and the deal card, a refusal shows in a bar fixed above
  Telegram's main button.
- Before, it was a line at the foot of the page, out of sight on a phone.

## Consequences

- Q-B8 (who reads details in full) and the sealing of legs (ADR-0004) have nothing left
  to apply to. `swap/crypto.py` and the key serve only the stored entries, until G7.
- A leg says how and by when, not where. Someone who needs a card number asks in
  Telegram.
- The way to a proposal has fewer screens and fewer required fields.

## Alternatives considered

- **Optional details.** Keeping the feature without requiring it still leaves a step in
  the way, and the owner said it isn't needed.
- **Narrowing the details form to the order's currency and ways.** This is G1's first
  half. It would stop entries in the wrong currency, but the step would remain.
- **Six ways, three of them shown.** Older orders would show ways that nobody can pick.
