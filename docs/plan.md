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
- [x] Phone check of links once PR 1.1 is deployed: create an invite and share it.
      Linking itself needs a second Telegram account. (Done in the demo, 2026-10-22.)
- [x] Keep a copy of the payment-details key off the server. No longer needed: the
      details and the key went in PR 1.16 (G7).
- [x] Phone check of PRs 1.8–1.11 once deployed: a new order without a minimum or a
      last day, with its rate filled in; then close, reopen and delete one.
- [ ] The demo, after slice 1: invite one or two people for a real link, order and
      deal. Links and an order worked on 2026-10-22; the deal waits for PRs 1.12–1.15.
- [x] Answer G7 in `docs/QUESTIONS.md`: may the four saved payment details, their table
      and the key be deleted? Yes, on 2026-10-22.
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
- [x] Migration: `payment_methods`. AES-GCM envelopes, with keys from the environment
      and the mask written alongside (ADR-0004).
- [x] api: list, add and delete one's own; tests that no one else reads them and that
      no log line holds them.
- [x] App: a profile screen behind the avatar with name, language and «Реквизиты».

**PR 1.6 — Deals: the state machine** (ADR-0018)
- [x] Migration: `deals`, `deal_legs`, `events` with its append-only trigger, and the
      trigger that refuses a status change without its event (ADR-0002; it fires at
      once, ADR-0018).
- [x] The state-machine service. Every transition of Q-B1 is tested, and so is every
      illegal one, cancel requests and disputes included (their screens are slice 4).
- [x] api: propose, accept, decline, withdraw, sent, received, cancel. Remainders
      follow FR-2.3 and Q-B5. Pending proposals that an order can no longer cover are
      cancelled (Q-E2).
- [x] Notifications for every deal event above.

**PR 1.7 — Deals: the proposal and the deal card**
- [x] The proposal: an amount slider within the remainder, the counter currency, who
      goes first, due dates, payment details picked or added on the spot, and the
      rounding tick (Q-B4).
- [x] The deal card: both legs, a status line that says what to do next, and actions
      behind `showConfirm`. The payer sees the details in full once the deal is
      accepted (Q-B8), with «Скопировать». An open card polls every 10 s until the
      deal is over, so the other side's step shows without reopening the app.
- [x] Home: my active deals, so the demo can find them without the bot.

**The owner's first test (2026-10-22).** He ran slice 1 on his own and sent seven
notes (QUESTIONS part F, ADR-0019). They change orders, so they come before the demo
with others.

**PR 1.8 — Orders: less to fill in** (F1, F3, F4)
- [x] Migration: `amount_min` may be 0, and `available_until` may be empty.
- [x] The currency lists open with «Отдаёте» and «Получаете».
- [x] An empty minimum is any amount; the last day sits behind «Ограничить срок», off
      by default.

**PR 1.9 — Orders: how the author is paid** (F2)
- [x] Migration: `orders.receive_methods`; orders published earlier get all six.
- [x] Step 2 asks for them, the card shows them, and a proposal pays in one of them.

**PR 1.10 — Orders: the market rate** (F5, ADR-0020)
- [x] api: Coinbase's public rates, cached, as one endpoint.
- [x] The wizard fills each rate in from it, with the source and time; the author can
      change it.

**PR 1.11 — Orders: reopen and delete** (F6, F7)
- [x] api: reopen a closed order; delete one that isn't open.
- [x] The order card offers both to its author.

**Demo.** Deploy, then stop and ask the owner to invite one or two people.

**The demo with others (2026-10-22).** Links and an order worked, but no proposal went
through (G5). The owner's notes are QUESTIONS part G, ADR-0021 and ADR-0022.

**PR 1.12 — Deals ask only what the exchange needs** (G1, G3, G4, G5; ADR-0021)
- [x] Migration: `deals.note`; the legs' payment details go.
- [x] The proposal starts at all that remains, asks for no payment details, and takes an
      optional comment. Accepting is one confirmation.
- [x] The profile without «Реквизиты»; what stops a form shows above the main button.

**PR 1.13 — Three ways: cash, bank, crypto** (G3; ADR-0021)
- [x] Migration: card, SBP and «other» become bank; the CHECKs allow three.

**PR 1.14 — A way on from a link's screen** (G6)
- [x] A made link's screen leads Home with the main button.

**PR 1.15 — The market rate by default** (G2; ADR-0022)
- [x] An order follows the market unless its author fixes the rate; whoever opens it
      sees the rate of the moment, and a proposal locks it.

**PR 1.16 — The saved payment details go** (G7; ADR-0021)
- [x] Migration: `payment_methods` is dropped, with its four entries.
- [x] The api, the sealing code, `new_key` and the `cryptography` dependency go;
      `RECIPIENT_KEYS` leaves `.env.example`, the deploy guide and the server.

**The first real deal (2026-10-22).** @format37 and irinayurasova ran one to «Получил» on
both sides. The owner's notes are QUESTIONS part H.

**PR 1.17 — Past orders stay** (H4; ADR-0023)
- [x] Whoever dealt on an order can still open it; proposing still needs it open to them.
- [x] Home folds finished orders under «Завершённые заявки»; an order's card lists its
      finished deals too.

**PR 1.18 — Both legs at once** (H1–H3; ADR-0024)
- [x] The proposal loses «who goes first» and the dates.
- [x] After acceptance, each side marks «Отправил» and «Получил» in any order; both
      receipts settle the deal.
- [x] The journal names the amount, currency and country of each transfer.

**Demo, again.** Deploy, then ask the owner to run the deal.

**PR 1.19 — Error reports** (I1; ADR-0025)
- [x] One Sentry project, `swap`; the api, the worker and the Mini App report to it.
- [x] Nothing personal: no bodies, no local variables, no initData, no bot token.
- [ ] Follow-up: readable Mini App stack traces. Build with `sourcemap: 'hidden'`, upload
      the maps with `@sentry/vite-plugin` in the image build (a Sentry auth token in the
      VPS's `.env`, passed as a build secret, never a build arg), and keep them out of
      `/assets`. Done when a production frontend issue shows `src/…` file and line.

### Slices 2–7

Each is broken into PRs when it starts.

| Slice | Content |
|---|---|
| 2 | Balances (Q-B2); the deals list, active and history; «требует моего действия» on Home; order editing (FR-2.5) and the feed's filters (FR-2.4), which ADR-0006 left unplaced |
| 3 | Documents through the bot (FR-5.1, 5.3–5.5, Q-B13) |
| 4 | Cancel requests, disputes and their resolution, deal notes (FR-4.5–4.7) |
| 5 | Reminders (Q-B7); order and proposal expiry; the in-app feed and its counter; muting a link's new orders; the retention and session sweeps; `requestWriteAccess` for those who skipped /start (Q-B12) |
| 6 | The manual rate (Q-B3); the profile's display name, time zone and default currencies; blocks and the block list; account deletion (Q-B10) |
| 7 | Encrypted off-box backups and a restore drill; hardening, including the rate limit on sign-in; the user agreement (Q-B15); Sentry source maps for the Mini App, if PR 1.19's follow-up is still open |

## Estimates

| Phase | Sessions | Calendar |
|---|---|---|
| 0 — skeleton | 4 (done) | 2026-10-21 to 2026-10-22 |
| 1 — MVP | ≈ 22.5 | ≈ 4 weeks; the last days wait on the group's real deal |

Phase 1 by slice (ADR-0006):

| Slice | Sessions |
|---|---|
| Links, the outbox (PRs 1.1–1.2) | 1.75 |
| Orders (PRs 1.3–1.4) | 2 |
| Payment details, deals, the state machine (PRs 1.5–1.7) | 3.75 |
| The owner's notes (PRs 1.8–1.11) | 1.5 |
| The demo's notes (PRs 1.12–1.16) | 1.5 |
| The first deal's notes (PRs 1.17–1.18) | 1 |
| **Demo** | **≈ 11.5** |
| Balances, lists, order editing and filters | 1.5 |
| Documents through the bot | 1.5 |
| Cancel, dispute, notes | 1 |
| Reminders, expiry, feed | 1.5 |
| Manual rate, profile, blocks, deletion | 1.5 |
| Backups, hardening, agreement | 1.5 |
| Georgian review, acceptance fixes | 1.5 |
| **Total** | **≈ 22.5** |

Slice 2 grew by half a session on 2026-10-22: order editing and the filters had no
slice. Slice 1 grew by one and a half the same day, for the owner's notes after his
first test, by one and a half again for his notes after the demo, and by one for his
notes after the first real deal.

## Phase 0 — skeleton (accepted 2026-10-22)

The owner signed in from his phone and accepted phase 0 on 2026-10-22. It shipped in
PRs #1–#7: the docs, the backend skeleton and CI, sign-in with `initData` and the
worker with the bot, the Mini App in three languages, the image, the local stack and
the VPS deploy. Its checklist is in this file's history.
