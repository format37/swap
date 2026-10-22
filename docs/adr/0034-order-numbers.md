# 0034. Every order has a number, «№ 17», from one sequence

Status: Accepted · Date: 2026-10-22 · Spec: §11; QUESTIONS K8

## Context

Orders have uuids (ADR-0002), which nobody can say out loud. The owner asked for an
identifier on every order (K8), so people can name one in a chat, and so the CSV export
(K4) and recurring copies (K7) can refer to it.

## Decision

- `orders.number` is a `bigint` from the sequence `order_numbers`, unique, filled by the
  database on insert. The ORM reads it back with the INSERT (`eager_defaults`).
- Migration 0022 numbers the existing orders in the order they were published, from 1,
  and starts the sequence after them.
- One sequence serves all orders, so a number says nothing about whose order it is. At
  Swap's scale it says little about volume either. ADR-0002 gave uuids that reason.
- It shows as «№ 17» (English «No. 17») on the order card, in order rows and on the deal
  card («Сделка по заявке № 17»). It is in the bot's messages about a new order and a
  proposal.
- The api's `Order.number` and `Deal.order_number` carry it. Links in the bot still open
  orders by uuid (ADR-0013).

## Consequences

- A sequence can skip a number when a transaction rolls back. A gap is harmless.
- Messages queued before the deploy have no number. The few that may wait in the outbox
  at that moment would fail to word themselves; the outbox sends within seconds, so the
  window is negligible.

## Alternatives considered

- **Numbers per author** («моя № 3»). They read nicely, but two orders would share a
  number, and a chat between two people would need the author too.
- **A short form of the uuid.** It is shorter, but still can't be said out loud.
