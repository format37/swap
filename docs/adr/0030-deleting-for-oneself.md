# 0030. Each side deletes for themselves, and the server erases what all have deleted

Status: Accepted · Date: 2026-10-22 · Spec: §3, §5, §7 «Приватность», «Целостность»; QUESTIONS J3, L4; amends ADR-0002 and ADR-0019

## Context

Until now only an order's author could delete it, and only once it wasn't open (F6,
ADR-0019). `orders.deleted_at` then hid the order from everyone, including the people
who had dealt on it, because `seen_by` checks it. Deals could not be deleted. The journal
was append-only, with no exception (ADR-0002).

The owner asked for deletion by each side, for themselves, of what is finished (J3). The
author deletes the whole order with its deals; a participant deletes their own deal.
There is no restore. The server erases a row once everyone it belongs to has deleted it.

## Decision

**Who deletes what.**
- **A participant**, someone who proposed on an order, deletes their own deal once it is
  over: settled, cancelled, declined, withdrawn or expired. It works even while the
  order is still open. A deal still running answers 409 `deal.running`, and the author
  asking to delete one deal answers 409 `deal.delete_with_order`. The app offers it on a
  finished deal's card as «Удалить у себя».
- **A participant, all at once** (L4): `DELETE /orders/{id}` from someone who isn't its
  author deletes all their own deals on it, each as above, once every one of them is
  over. One still running answers 409 `deal.running`, and someone with no deal on it gets
  404. The app offers it on the order's card as «Удалить у себя», and the order then
  leaves their history.
- **The author** deletes the whole order with all its deals, once the order is no longer
  open and none of its deals runs. Otherwise the answer is 409 `order.open` or
  `order.deals_running`. The order card offers it only then.

**What is recorded.** The author's deletion is per order: `orders.deleted_at`, now
"deleted by its author, for its author". A participant's is per deal:
`deals.proposer_deleted_at`.

**What each one sees.**
- Whoever deleted something gets 404 for it, as for a thing that doesn't exist.
  Everyone else sees no change.
- Feeds and deal lists leave out what the viewer deleted.
- A participant's history finds an order through their deals that they haven't deleted.
  An order its author deleted stays in the history of everyone who dealt on it. That
  includes orders deleted before this change, whose participants see them again.
- A deal of an order its author deleted is gone for the author once it is over. Only
  orders deleted before this change can have a deal still running, and the author keeps
  that deal until it ends.

**Erasing.** In the same transaction as the deletion that completes it:
- a deal is erased once its proposer has deleted it and its author has deleted the
  order;
- an order is erased once its author has deleted it and none of its deals remain;
- legs, journal lines and notifications go with them. Notifications are found by their
  card, `deal_<id>` or `order_<id>`.

There is no sweep and no timer.

**The journal's one exception.** `events` stays append-only, with one exception: erasing
a whole deal. Its foreign key to `deals` cascades, and the trigger lets a line go only
once its deal no longer exists. A stray `DELETE FROM events` still fails, and so do
UPDATE and TRUNCATE.

**No way back.** There is no restore and no sharing back. The other side can send a
screenshot. The bot's messages stay in each person's chat, and people delete them
themselves.

## Consequences

- An erased deal leaves no trace on the server, except in the deploy-time dumps, the
  last five, until they rotate out. The privacy page says so (K3).
- A score (ADR-0029) loses the point of an erased deal.
- A deal deleted by one side only stays whole for the other, journal and all.
- Account deletion (K2, Q-B10) builds on this: everything finished counts as deleted by
  the person leaving.

## Alternatives considered

- **Hiding without erasing.** Rows nobody can see would stay on the server forever, and
  the owner asked for erasure once everyone has deleted.
- **A restore on request to whoever hasn't deleted yet.** The owner dropped it: «удалил -
  сам виноват».
- **A session switch that opens the journal for deletes** (`SET LOCAL swap.erasing`).
  Any code could flip it. "Its deal is gone" is a rule the database checks itself.
- **A sweep that erases later.** Doing it in the deleting transaction means no job, and
  nothing waits half done.
