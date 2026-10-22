# 0024. A deal's two transfers run at once, with no order and no dates

Status: Accepted · Date: 2026-10-22 · Spec: §5, FR-4.1, FR-4.3–4.5, §11; QUESTIONS H1–H3; amends ADR-0018 and Q-B1

## Context

Q-B1 made the legs strictly sequential: leg 1's «Отправил» and «Получил», then leg 2's.
Who went first was a proposal field (Q-B16), and each leg had a due date. After the first
real deal the owner asked for the opposite (H1, H2):
- Both people pay and both get paid. Each should have both buttons at once, and decide
  for themselves who sends when.
- They confirm as the money arrives.
- No «who goes first», no dates.

He also wants the journal to say what moved, which the deal already knows (H3).

## Decision

**Six statuses:** proposed, accepted, disputed, settled, cancelled and expired.
`leg1_sent`, `leg1_received` and `leg2_sent` go. While a deal is accepted, its legs carry
their own progress in `sent_at` and `received_at`.

**Each leg on its own, in any order:**
- «Отправлено» is the payer's, once, on a leg not yet received.
- «Получено» is the payee's, once, whether or not the payer marked it sent. Money that
  arrived was sent, so a receipt fills in `sent_at` too, and `ck_deal_legs_sent_first`
  stands.
- The receipt that leaves nothing outstanding settles the deal and notifies the other
  side (`deal.settled`). Earlier marks notify as before (`deal.sent`, `deal.received`).
- Leg 1 is always the proposer's transfer and leg 2 the author's. The numbers only name
  them.

**Cancelling (FR-4.5)** is alone while nothing has moved, and needs both once anything
has. "The first «Отправил»" becomes "any mark on either leg".

**No dates.** `deal_legs.due_date` becomes nullable, and new deals leave it empty. The
proposal loses `first`, `my_due` and `their_due`. Slice 5's reminders (Q-B7) will need
another clock, such as days since acceptance.

**The journal** (H3). The api's `DealEvent.to` becomes a plain string, because older
lines name states that no longer exist and the journal is never rewritten. The app writes
a transfer's line as «Отправлено: 1 712,33 GEL · Грузия · Nino B», from the leg the event
names.

**The app.** The deal card no longer puts these steps in the main button: each leg's card
carries the viewer's mark, «Деньги отправлены» on what they pay and «Деньги получены» on
what they get, each behind `showConfirm`. The status line says what is left: both marks,
one of them, or whom we wait for.

**Migration 0014** moves any deal still in an old state to accepted, with a
`legs_at_once` event so the journal trigger lets it through. Production had none. It
narrows the status CHECK and drops NOT NULL from `due_date`.

## Consequences

- Each transfer now has its own sent and received times, which history and slice 2's
  balances can use.
- The exhaustive state test covers 13 actions in 8 situations: the six states, and an
  accepted deal with a mark on leg 1.
- Nothing protects the side that pays first any more. Among people who invited each
  other (§3), the owner prefers that freedom to a forced order.

## Alternatives considered

- **Statuses for every combination of marks.** That would be nine states for one deal
  holding two independent flags.
- **Keeping the order with both buttons visible.** The owner's point was that the order
  isn't his business to set.
