# Swap — delivery plan

Phases are strictly sequential (§12). A phase starts only after the previous one's
acceptance criteria are met and the owner has confirmed. This file holds the current
phase's checklist and the estimates. Phase 1's order is ADR-0006.

A **session** here is one sitting of mine that ends in reviewable PRs with green CI,
roughly 2–4 hours of wall-clock work.

## Phase 1 — MVP (started 2026-10-22)

Phase 1 is done when parts J and K of `docs/QUESTIONS.md` are live and the owner
confirms (K10, a default). All of them went live on 2026-10-22 (PRs 1.20–1.30); what
remains is the owner's part below. §12's own checklist leaned on a document through the bot, a
balance and a restored backup. Those wait in «Потенциальные планы» below, and the rest of
the checklist goes with them. Its other items already hold: the first real deal settled
on 2026-10-22 (part H), and every transition of the state machine is tested.

Each PR carries its API, UI and tests, with every string in ru, en and ka, and is
usable on the bot once merged (ADR-0006). After a merge with green CI I redeploy
Swap's stack on the VPS and go on to the next PR (the owner's standing go, CLAUDE.md).

### Owner

- [ ] Answer part E of `docs/QUESTIONS.md`: three items, each with a default I follow
      until you answer.
- [x] Phone check of links once PR 1.1 is deployed: create an invite and share it.
      Linking itself needs a second Telegram account. (Done in the demo, 2026-10-22.)
- [x] Keep a copy of the payment-details key off the server. No longer needed: the
      details and the key went in PR 1.16 (G7).
- [x] Phone check of PRs 1.8–1.11 once deployed: a new order without a minimum or a
      last day, with its rate filled in; then close, reopen and delete one.
- [x] The demo, after slice 1: invite one or two people for a real link, order and
      deal. Links and an order worked on 2026-10-22, and the first real deal settled
      the same day (part H).
- [x] Answer G7 in `docs/QUESTIONS.md`: may the four saved payment details, their table
      and the key be deleted? Yes, on 2026-10-22.
- [ ] A phone check of PRs 1.17 and 1.18, and of each visible change after them. I ask
      for each one as it ships.
- [x] Your veto, if any, on part J's defaults: mainly reach 2 for new orders, rings
      instead of a web of lines, and proposals across handshakes. None (part L).
- [x] K6: what did you find missing in switching the language? A visible way to the
      settings, and back to Telegram's language (L5, L6).
- [x] Set the privacy page's URL in BotFather: https://swap.latentstate.dev/privacy
      (live since PR 1.27). Done on 2026-10-22.
- [ ] A phone check of PRs 1.20–1.30: the two-step wizard and its reach slider, photos
      and scores, «Удалить у себя», the settings (notifications, deleting, CSV,
      «О Swap»), the agreement at launch, order numbers, a recurring order.
- [ ] A phone check of PRs 1.31–1.35: the «Настройки» tab and «Как в Telegram»,
      «Удалить у себя» on an order you only dealt on, «Как получать» on each currency,
      typing «Получите», and whether Ira's photo now shows in the rings (L3).
- [x] Turn on «Prevent Storing of IP Addresses» in Sentry (ADR-0025). Done on
      2026-10-22, for the whole organization, the only place it could be set.
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

**The owner's notes and priority list (2026-10-22, evening).** Five notes on slice 1 are
QUESTIONS part J and ADRs 0026–0030; the priority list for the rest of the phase is part
K. Sentry (K5) was done already, in PR 1.19. Everything else moves to «Потенциальные
планы» below.

**PR 1.20 — The wizard in two steps, a rate per wanted currency** (J1; ADR-0026)
- [x] Migration: `order_wants.rate_spec`, copied from each order's spec; `orders.rate_spec`
      goes.
- [x] api: a spec per wanted currency in the draft and the order; the quote and the
      proposal use the chosen currency's. A currency appears once.
- [x] Step 1: «Отдаёте» and «Получаете» as two groups without section titles, and
      «Зафиксировать курс» per currency, off by default.
- [x] Step 2: the digest of step 1, «Кому видно» and the comment.

**PR 1.21 — People with photo, name and @username** (J4; ADR-0027)
- [x] Migration: `users.photo_url`, taken from `initData` at every sign-in. The CSP's
      `img-src` gains `https://t.me` and its CDN, `*.telesco.pe`.
- [x] One `Person` component everywhere a person is shown, with initials when there is
      no photo.
- [x] `dev_launch --photo`. After the deploy, count who has a photo: two of three
      had a link by the evening, Ira's photo and the owner's letter picture (L3).

**PR 1.22 — Reach by handshakes** (J2; ADR-0028)
- [x] Migration: `orders.reach`; 1 for orders without a list, 0 for those with one.
- [x] Visibility through a recursive CTE over active links. Negative tests first: one
      ring too far, a broken link in the middle of a chain, an order at 0 and someone
      not on its list, the filter.
- [x] api: the reach in the draft, `within` on «Открытые мне», the chain on the card,
      and the rings for the wizard.
- [x] App: the slider on step 2 with who will see the order and the rings; the folded
      filter on Home; the chain on the card.
- [x] The bot tells direct links only, and the words about links follow the new rule.

**PR 1.23 — The score** (J5; ADR-0029)
- [x] api: each person's score, counted from settled deals.
- [x] In `Person`, beside the name, with a tap that explains it.

**PR 1.24 — Deleting for oneself** (J3; ADR-0030)
- [x] Migration: `deals.proposer_deleted_at`. The journal lets a deal's lines go with the
      whole deal, and in no other way.
- [x] api: a participant deletes a finished deal; the author deletes a finished order
      with all its deals; the server erases what both sides have deleted.
      Authorization tests first.
- [x] The deal card and the order card offer it.

**PR 1.25 — The settings: notifications and the language** (K1, K6)
- [x] Migration: what each person switched off, and whose new orders they muted.
- [x] The settings on the profile screen: «Все уведомления» and a switch per kind;
      «Язык». Muting a link's new orders on its screen.
- [x] The outbox skips what the recipient switched off.

**PR 1.26 — Deleting all history, and the account** (K2; Q-B10)
- [x] «Удалить всю историю»: J3 for everything finished, and a word on what still runs.
- [x] «Удалить аккаунт»: refused while a deal runs; proposals cancelled, orders closed,
      links, invites and sessions deleted, history deleted as J3 has it; the row
      becomes «Удалённый участник».

**PR 1.27 — The agreement, the privacy page, the contact** (K3, K9; Q-B15)
- [x] The agreement at first launch, with «Принимаю», in ru, en and ka.
- [x] https://swap.latentstate.dev/privacy, a plain page in three languages. Its URL goes
      to the owner.
- [x] The settings link to it, and offer format37@gmail.com with «Скопировать».

**PR 1.28 — Order numbers** (K8)
- [x] Migration: `orders.number` from one sequence; existing orders numbered by age.
- [x] «№ 17» on cards, rows and deals, and in bot messages.

**PR 1.29 — CSV export** (K4; FR-6.3)
- [x] One row per deal the user took part in, in their language.
- [x] The bot sends the file to their chat.

**PR 1.30 — Recurring orders** (K7)
- [x] «Повторять каждый месяц, N-го числа» in the wizard.
- [x] A worker job publishes each copy on its day, once, and announces it.
- [x] «Больше не повторять» on any copy.

**After the list (2026-10-22).** A pass over the profile at 390 px in headless Chrome
wrapped its long rows and set the deletions apart (#41). Two checks wait on people
signing in again: how many users get a `photo_url` (ADR-0027), and that the agreement
shows once.

**The owner's notes after testing parts J and K (2026-10-22).** QUESTIONS part L. No
veto on parts J and K. All five PRs went live the same evening (#44–#48), with migration
0024; a pass at 390 px in headless Chrome checked the wizard's currency cards, the order's
card and the tab bar.

**PR 1.31 — A settings tab, and the language Telegram has** (L5, L6; ADR-0039)
- [x] «Настройки» becomes a tab beside «Главная» and «Связи».
- [x] The language screen offers «Как в Telegram», and the api lets a chosen language go.

**PR 1.32 — Deleting a finished order one only dealt on** (L4; ADR-0030)
- [x] `DELETE /orders/{id}` deletes, for someone who dealt on it, all their finished deals
      on it; the order's card offers «Удалить у себя».

**PR 1.33 — How to be paid, per currency** (L1; ADR-0037)
- [x] Migration: `order_wants.receive_methods`, copied from the order's; the order's set
      goes.
- [x] The wizard's and the order's cards show each currency's ways; a proposal pays in one
      of the chosen currency's.

**PR 1.34 — Write what one gets, and let it be typed** (L2; ADR-0038)
- [x] `POST /quote` works the other way too: what to give for an amount wanted.
- [x] Each wanted currency's card holds «Получите», a field that sets what is given, and
      the other currencies follow.

**PR 1.35 — Keep a photo's link when a launch brings none** (L3; ADR-0027)
- [x] The sign-in keeps the stored link when a launch has none, and still takes a new
      one, Telegram's letter picture included.

### Потенциальные планы: not now

The owner moved everything below off the plan on 2026-10-22 (QUESTIONS K). None of it is
built until the owner brings it back.

**From slices 2–7:**
- balances (Q-B2);
- the deals list, active and history, and «требует моего действия» on Home;
- order editing (FR-2.5), and the feed's filters by currency and country (FR-2.4);
- documents through the bot (FR-5.1, 5.3–5.5, Q-B13);
- the cancel-request and dispute screens, whose api exists, and deal notes (FR-4.7);
- reminders (Q-B7);
- order and proposal expiry (FR-2.6, FR-4.4);
- the in-app feed and its counter (FR-7.3);
- the retention and session sweeps;
- `requestWriteAccess` for whoever skipped /start (Q-B12);
- the manual rate (Q-B3);
- the profile's time zone and default currencies;
- blocks and the block list (FR-1.4);
- off-box encrypted backups and the restore drill (Q-A7: the bucket and the `age` key);
- hardening, including the rate limit on sign-in.

**From v1 and v2:**
- NBG and CBR with a markup (FR-3.3);
- match hints (FR-8.1);
- counter-proposals (FR-4.2);
- uploads from the app (FR-5.2);
- browser sign-in (Q-C3);
- netting (FR-8.2);
- quiet hours (FR-7.2);
- favourites, with the feed filter's 0 (J2).

**Flagged to the owner on 2026-10-22:** without off-box backups, the only copies are the
deploy-time dumps, the last five, on the same VPS. They survive a bad migration, not a
lost server.

## Estimates

| Phase | Sessions | Calendar |
|---|---|---|
| 0 — skeleton | 4 (done) | 2026-10-21 to 2026-10-22 |
| 1 — MVP | ≈ 25 | ≈ 2 more weeks, then the owner's confirmation |

Phase 1, PR by PR:

| PRs | Item | Sessions |
|---|---|---|
| 1.1–1.18 | Slice 1 and three rounds of the owner's notes | 11.5 (done) |
| 1.19 | Error reports (part I) | 0.5 (done) |
| 1.20 | J1 · the wizard in two steps, a rate per wanted currency | 1 |
| 1.21 | J4 · people with photo, name and @username | 0.5 |
| 1.22 | J2 · reach by handshakes, the feed's filter, the rings | 1.5 |
| 1.23 | J5 · the score | 0.5 |
| 1.24 | J3 · deleting for oneself, and erasing once all have | 1 |
| 1.25 | K1, K6 · the settings: notifications and the language | 1 |
| 1.26 | K2 · deleting all history, and the account | 1 |
| 1.27 | K3, K9 · the agreement, the privacy page, the contact | 0.75 |
| 1.28 | K8 · order numbers | 0.25 |
| 1.29 | K4 · CSV export | 0.5 |
| 1.30 | K7 · recurring orders | 0.75 |
| 1.31 | L5, L6 · a settings tab, and Telegram's language | 0.5 |
| 1.32 | L4 · deleting a finished order one only dealt on | 0.5 |
| 1.33 | L1 · how to be paid, per currency | 1 |
| 1.34 | L2 · the amount one gets, typed | 1 |
| 1.35 | L3 · keeping a photo's link | 0.25 |
| | Georgian review, acceptance fixes | 1 |
| | **Total** | **≈ 25** |

On 2026-10-22 the owner's notes and priority list replaced slices 2–7: their 8.5
sessions gave way to about 9 for parts J and K. K6 is folded into the settings PR, and
K9 into the privacy page's, because each touches the same screens. The owner's notes
after testing them (part L) add about 3.25.

## Phase 0 — skeleton (accepted 2026-10-22)

The owner signed in from his phone and accepted phase 0 on 2026-10-22. It shipped in
PRs #1–#7: the docs, the backend skeleton and CI, sign-in with `initData` and the
worker with the bot, the Mini App in three languages, the image, the local stack and
the VPS deploy. Its checklist is in this file's history.
