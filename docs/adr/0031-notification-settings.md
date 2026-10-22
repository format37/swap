# 0031. Notification settings: switches on the person, mutes per pair, the outbox obeys

Status: Accepted · Date: 2026-10-22 · Spec: FR-7.1, FR-7.2; QUESTIONS K1, K6; ADR-0014

## Context

The bot tells people about every event of FR-7.1 (ADR-0014). The owner asked for a way
to switch everything off and to choose by type, «и др.» (K1). FR-7.2 already asked for
muting one link's new orders, and Q-B6 put that in the MVP. Quiet hours stay in
«Потенциальные планы».

## Decision

**What is kept.**
- `users.notifications_off`: «Все уведомления», off.
- `users.muted_kinds`: the kinds switched off one by one. There are five, which is the
  default reading of «по типам сделок»: new orders, links, proposals and answers,
  transfers, cancellations and disputes. A CHECK keeps the list to them.
- `mutes (user_id, muted_id)`: one person hears nothing of another's new orders.

**Which switch a message answers to** is one table, `KIND_OF` in
`swap/notifications.py`. A test holds it to the bot's dictionary, so a new message type
can't be added without a switch.

**Who obeys.**
- The outbox checks the switches when it sends: a message switched off is `skipped`,
  with «switched off» as the reason. Switching off also stops what is already queued.
- A mute is applied when an order is published: the muting person isn't told. Their feed
  still shows the order, because a mute is about messages, not visibility.

**Where.** The profile behind Home's avatar holds the settings (K1): «Уведомления», which
opens a screen of switches, and «Язык», which exists since phase 0 (K6). A link's screen
has «Сообщать о новых заявках» for that person.

**api.** `PATCH /me` takes `notifications_off` and the whole `muted_kinds` list.
`PUT` and `DELETE /links/{id}/mute` mute and unmute the person on a link's other side;
anyone outside the pair gets 404.

## Consequences

- In-app notices don't exist yet (FR-7.3 waits in «Потенциальные планы»), so a switched-
  off message is simply not delivered. The app still shows every change.
- A message the user asked for, such as K4's CSV, answers to no switch.

## Alternatives considered

- **One `notify` JSON on the user.** It is shorter to add, but the database can't check
  it, and a list of kinds is all it would hold.
- **Filtering when queueing instead of when sending.** Mutes do that, since they belong
  to the publishing moment; kinds are checked at sending, so «Все уведомления» acts at
  once.
