# Swap — delivery plan

Phases are strictly sequential (§12). A phase starts only after the previous one's
acceptance criteria are met and the owner has confirmed. This file holds the current
phase's checklist and the estimates. Phase 1's order is ADR-0006.

A **session** here is one sitting of mine that ends in reviewable PRs with green CI,
roughly 2–4 hours of wall-clock work.

## Phase 1 — MVP (started 2026-10-22)

Phase 1 is done when the owner and three acquaintances have run one real deal end to
end, from the order to both «Получил», and §12's checklist holds:
- three links made by invite links, and one by a request to an @username;
- an order is visible to the author's links and to nobody else, and a test proves it;
- a deal was proposed and accepted, both legs were marked, and a document was attached
  through the bot;
- the balance showed the open obligation and returned to zero after «Получил»;
- every transition of the state machine is tested, and illegal ones are refused;
- a backup was restored into a clean container.

Each PR carries its API, UI and tests, with every string in ru, en and ka, and is
usable on the bot once merged (ADR-0006). After a merge with green CI I redeploy
Swap's stack on the VPS (the kickoff's standing permission).

### Owner

- [ ] Answer part E of `docs/QUESTIONS.md`: three items, each with a default I follow
      until you answer.
- [ ] Phone check of links once PR 1.1 is deployed: create an invite and share it.
      Linking itself needs a second Telegram account.
- [ ] Keep a copy of the payment-details key off the server. PR 1.5 generates it on
      the VPS, and without it the saved details can't be read back (ADR-0004).
- [ ] The demo, after slice 1: invite one or two people for a real link, order and
      deal.
- [ ] By slice 5: the backup bucket and the `age` public key (Q-A7).
- [ ] Before acceptance: a native speaker's read of the Georgian strings, the device
      list (Q-A6), and the agreement text (Q-B15).

### Slice 1 — the demo: link + order + deal, without documents

The outbox moves up from step 4 into links, because a request to an @username is
invisible without a notification (ADR-0014). Each later PR sends its own
notifications.

**PR 1.1 — Links by invitation** (ADR-0012, ADR-0013, ADR-0015)
- [x] Migration: `links` and `invites`.
- [x] api: create and revoke an invite (at most 10 outstanding), list links, view one
      with the mutual-links count, accept, decline, and break or withdraw.
      Authorization tests come first: a stranger gets 404 on everything.
- [x] Bot: `/start inv_<token>` turns the invite into a request, then greets the
      invitee with the inviter's name and «Открыть».
- [x] App: the tab bar; the «Связи» tab; the invite sheet with share and copy; the
      request screen; deep links from `startapp`.
- [x] Dev: the Telegram mock draws MainButton, BackButton and popups, so they can be
      clicked in Chrome.

**PR 1.2 — The outbox, and requests by @username** (ADR-0014)
- [x] Migration: `notifications`.
- [x] Worker: the outbox sweep every 5 s. It claims rows with `SKIP LOCKED`; a 429
      waits, a 403 turns `can_message` off, and other failures back off.
- [x] Notifications for a link request and an established link.
- [x] api and app: a request to an @username, with the 7-day cooldown (Q-E1).

**PR 1.3 — Orders: model, visibility, rates** (ADR-0016)
- [x] Migration: `orders`, `order_wants`, `order_visibility`; `users.tz`, taken from the
      device. `events` and its trigger move to PR 1.6: only deals journal in slice 1.
- [x] `rate_spec` v1 (fixed), and `swap/rates.py` with its tests.
- [x] api: create, list («открытые мне» / «мои»), view, close, and a quote for live
      previews. Visibility tests come first: not linked, link broken, not in the
      order's list.
- [x] A notification: a new order is open to you.

**PR 1.4 — Orders: the wizard, the card, Home** (ADR-0017)
- [x] The three-step wizard with a fixed rate and a live preview, and the order card.
- [x] Home: «Открытые мне» and «Мои»; the three-step empty state.
- [x] Assets with their symbol, code and flag (ADR-0003).

**PR 1.5 — Payment details** (ADR-0010)
- [ ] Migration: `payment_methods`. AES-GCM envelopes, with keys from the environment
      and the mask written alongside (ADR-0004).
- [ ] api: list, add and delete one's own; tests that no one else reads them and that
      no log line holds them.
- [ ] App: a profile screen behind the avatar with name, language and «Реквизиты».

**PR 1.6 — Deals: the state machine** (ADR-0018, written with it)
- [ ] Migration: `deals`, `deal_legs`, `events` with its append-only trigger, and the
      deferred trigger that refuses a status change without its event (ADR-0002).
- [ ] The state-machine service. Every transition of Q-B1 is tested, and so is every
      illegal one, cancel requests and disputes included (their screens are slice 4).
- [ ] api: propose, accept, decline, withdraw, sent, received, cancel. Remainders
      follow FR-2.3 and Q-B5. Pending proposals that an order can no longer cover are
      cancelled (Q-E2).
- [ ] Notifications for every deal event above.

**PR 1.7 — Deals: the proposal and the deal card**
- [ ] The proposal: an amount slider within the remainder, the counter currency, who
      goes first, due dates, payment details picked or added on the spot, and the
      rounding tick (Q-B4).
- [ ] The deal card: both legs, a status line that says what to do next, and actions
      behind `showConfirm`. The payer sees the details in full once the deal is
      accepted (Q-B8), with «Скопировать».
- [ ] Home: my active deals, so the demo can find them without the bot.

**Demo.** Deploy, then stop and ask the owner to invite one or two people.

### Slices 2–7

Each is broken into PRs when it starts.

| Slice | Content |
|---|---|
| 2 | Balances (Q-B2); the deals list, active and history; «требует моего действия» on Home; order editing (FR-2.5) and the feed's filters (FR-2.4), which ADR-0006 left unplaced |
| 3 | Documents through the bot (FR-5.1, 5.3–5.5, Q-B13) |
| 4 | Cancel requests, disputes and their resolution, deal notes (FR-4.5–4.7) |
| 5 | Reminders (Q-B7); order and proposal expiry; the in-app feed and its counter; muting a link's new orders; the retention and session sweeps; `requestWriteAccess` for those who skipped /start (Q-B12) |
| 6 | The manual rate (Q-B3); the profile's display name, time zone and default currencies; blocks and the block list; account deletion (Q-B10) |
| 7 | Encrypted off-box backups and a restore drill; hardening, including the rate limit on sign-in; the user agreement (Q-B15) |

## Estimates

| Phase | Sessions | Calendar |
|---|---|---|
| 0 — skeleton | 4 (done) | 2026-10-21 to 2026-10-22 |
| 1 — MVP | ≈ 18.5 | ≈ 4 weeks; the last days wait on the group's real deal |

Phase 1 by slice (ADR-0006):

| Slice | Sessions |
|---|---|
| Links, the outbox (PRs 1.1–1.2) | 1.75 |
| Orders (PRs 1.3–1.4) | 2 |
| Payment details, deals, the state machine (PRs 1.5–1.7) | 3.75 |
| **Demo** | **≈ 7.5** |
| Balances, lists, order editing and filters | 1.5 |
| Documents through the bot | 1.5 |
| Cancel, dispute, notes | 1 |
| Reminders, expiry, feed | 1.5 |
| Manual rate, profile, blocks, deletion | 1.5 |
| Backups, hardening, agreement | 1.5 |
| Georgian review, acceptance fixes | 1.5 |
| **Total** | **≈ 18.5** |

Slice 2 grew by half a session on 2026-10-22: order editing and the filters had no
slice.

## Phase 0 — skeleton (accepted 2026-10-22)

The owner signed in from his phone and accepted phase 0 on 2026-10-22. It shipped in
PRs #1–#7: the docs, the backend skeleton and CI, sign-in with `initData` and the
worker with the bot, the Mini App in three languages, the image, the local stack and
the VPS deploy. Its checklist is in this file's history.
