# 0023. An order's history stays open to whoever dealt on it

Status: Accepted · Date: 2026-10-22 · Spec: §3, FR-2.4; QUESTIONS H4; amends ADR-0016

## Context

After the first real deal, @format37 went back from it and met «Заявка не найдена». The
order had been used up. ADR-0016's one visibility predicate shows an order to anyone but
its author only while it is open. That rule is right for taking an order up. It is wrong
for looking back at one that is over, and to the user it looked like an error (H4).

## Decision

**Two predicates in `swap/orders.py`:**
- `open_to(viewer)` is ADR-0016's rule unchanged: the author, or a link while the order
  is open, in its dates and on its list. The «Открытые мне» feed and proposals use it.
- `seen_by(viewer)` adds whoever proposed a deal on the order, of any outcome. The card
  and the history use it.

Going back from a deal therefore always finds its order. Proposing again still needs
`open_to`, so a broken link (Q-B9) or a closed order refuses as before. A deleted order
is still nobody's (F6).

**Feeds:**
- `mine` lists the author's open orders.
- `history` lists the finished ones, the author's own and those the viewer dealt on,
  most recently changed first.
- Home folds the history under «Завершённые заявки (N)», closed by default. A row there
  says whose order it was and how it ended.

**An order's card lists every deal on it.** `GET /deals?scope=all&order_id=…` returns
the finished ones too.

## Consequences

- A proposer keeps reading a closed order's terms, the rate and the note. They read them
  when they proposed.
- Finished orders have a home, so «Мои заявки» shows only what is open.

## Alternatives considered

- **A page of its own for past orders.** The owner offered it, but it would add a screen
  and a route to reach it. The fold sits where people already look.
- **Showing the history only to the author.** It wouldn't fix the error, which was the
  proposer's.
