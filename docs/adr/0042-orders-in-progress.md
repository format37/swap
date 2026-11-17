# 0042. An order no longer open whose deal runs is in progress, not finished

Status: Accepted · Date: 2026-11-17 · Spec: FR-2.4; QUESTIONS P1; amends ADR-0023

## Context

ADR-0023 split Home's orders by status alone: `mine` held the author's open orders, and
`history` everything no longer open, folded under «Завершённые заявки». An order is used
up when accepting a deal leaves less than its smallest deal (Q-B5), long before that
deal is settled. The owner's order № 9, for exactly its minimum, went to the finished
ones the moment he accepted its one deal, and read «Исполнена» while nothing had been
sent (P1). He asked for a group for such orders.

## Decision

**One predicate, `running_for(viewer)` in `swap/orders.py`:** a deal on the order is
proposed, accepted or disputed, and the viewer is one of its two sides. For the author
that is any deal on the order; for anyone else, only their own.

**Feeds:**
- `running` lists the orders no longer open, as `seen_by` allows, for which
  `running_for` holds, latest change first.
- `history` lists the rest of them, as before.
- `mine` is unchanged: an open order with a deal running stays there, since it still
  takes proposals.

**Every order says `running`,** in lists and on its card. A row or card of an order no
longer open says «В работе» instead of its status while it is true.

**Home** shows the `running` orders as «Заявки в работе», unfolded, after «Мои заявки»
and before the fold of finished ones.

## Consequences

- An order moves from «Заявки в работе» to «Завершённые заявки» when its last running
  deal is settled or cancelled, without a change to the order itself. Deal actions
  refresh the order lists already.
- A closed order whose accepted deal runs is in progress too. Its card still offers to
  reopen it.
- Someone whose own deal on an order is over sees it finished, though the author's deal
  with another person still runs: the author's other deals are not theirs to see.
- The order's status keeps its meaning: whether it takes proposals. «В работе» is a
  label over it, not a fifth status, so the state machines are untouched.

## Alternatives considered

- **Keeping such orders in «Мои заявки».** That group is the author's open orders, the
  ones others may still take up, and it would leave out those who only dealt on one.
- **A new order status.** Every deal's end would then have to move its order back, and
  ADR-0016's statuses say whether an order takes proposals, which this doesn't change.
- **Working it out in the browser from the card's deals.** The card would first say
  «Исполнена» and then change, and lists would need every order's deals.
