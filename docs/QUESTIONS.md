# Questions for the owner

Each item ends with a proposed default. **"ok" accepts it**; anything else replaces
it. Answer under **Answer:** or in the PR review. Once answered, an item is folded
into an ADR (or the code) and marked here with the date. Nothing is deleted.

- **Part A** blocks phase 0. If you only have a minute, answer A1–A6 and A8.
- **Part B** blocks phase 1 (MVP).
- **Part C** is for later phases and needs no answer now.
- Items marked §13 are the spec's own owner questions.

## A. Before phase 0

### Q-A1 · The token in `.env` belongs to the production bot

`getMe` on the token in this repo's `.env` returns `@peertopeerswapbot` ("swap"),
the production bot, not a test bot. I made only that call and `getWebhookInfo` (no
webhook set, nothing pending), and I will call nothing else with it.

**Proposed:**
1. Create a test bot and put its token in `.env` as `TELEGRAM_BOT_TOKEN`.
2. Move the production token off this machine. It belongs only in the VPS `.env`,
   from MVP acceptance on.
3. While in BotFather:
   - Enable the test bot's Main Mini App (Bot Settings → Configure Mini App).
     `?startapp=` invite links need it. The production bot has none yet
     (`has_main_web_app: false`).
   - Turn off «Allow Groups» on both bots (`/setjoingroups`). Today the production
     bot can be added to groups, and §10 says the bot ignores groups anyway.

**Answer:**

### Q-A2 · GitHub repository

**Proposed:** a private `format37/swap`, like phonyx. I create it with `gh`, push
`main`, protect `main` (PR and green CI required), and open these docs as the first
PR.

**Answer:**

### Q-A3 · Production behind the existing `reverse-proxy`, not a Caddy of our own

§9 lists four containers, including Caddy. On the VPS, one Caddy 2.8 already owns
:80/:443 for every site.

**Proposed (ADR-0001):**
- Locally, compose runs its own Caddy, as the phase-0 DoD says.
- On the VPS, Swap is api + worker + postgres (+ backup in phase 1) on `mcp-shared`,
  with no host ports. `deploy/Caddyfile-swap.caddy` is appended to the shared
  Caddyfile, as phonyx does.
- The frontend is built into the api image and served by the api, so the block has
  one upstream.
- Its headers differ from the other sites in one way: no `X-Frame-Options: DENY`,
  because Telegram Web shows Mini Apps in an iframe. CSP `frame-ancestors` does that
  job instead.

**Answer:**

### Q-A4 · Session: a bearer token held in memory instead of a `SameSite=None` cookie

§7 asks for a `__Host-` cookie with `SameSite=None` "for the WebView". That attribute
is unnecessary in one kind of client and not enough in the other:
- On iOS, Android and Desktop the Mini App is a top-level page, so a cookie works
  there without `None`.
- On Telegram Web the app runs in an iframe on `web.telegram.org`, which is a
  third-party context. There a cookie needs `SameSite=None`, and for Safari also
  `Partitioned` (supported again only since Safari 26.2). Browsers that block
  third-party cookies outright, such as Brave, drop it anyway. And `SameSite=None`
  means every cross-site request carries the session, so we would need CSRF tokens on
  top.

The app re-sends `initData` at every launch anyway (§10).

**Proposed:**
- `POST /api/v1/auth/telegram` returns an opaque token, stored hashed with the
  30-day sliding expiry from §7.
- The token is kept in JS memory only and sent as `Authorization: Bearer`. No
  cookie, no CSRF surface, and the same behaviour in every client.
- A 401 re-authenticates once with the launch's `initData`. If that is more than an
  hour old, the app asks the user to reopen it.

**Answer:**

### Q-A5 · How a phone reaches the dev stack

Telegram needs a public HTTPS URL for the Mini App and for the webhook. The options:
- **Quick tunnel** (cloudflared, random URL per run). It works for the menu button,
  which a script can re-point. It doesn't work for `?startapp=` links: those open the
  Main Mini App URL set by hand in BotFather, so invites couldn't be tested locally.
- **ngrok's free plan** shows an interstitial page to browser traffic, and the
  WebView would show that page.

**Proposed:** a named Cloudflare tunnel, `swap-dev.latentstate.dev` → this machine.
It is stable, free and has no interstitial. From you it needs:
- `cloudflared tunnel login`, once, in a browser here. I install `cloudflared` into
  `~/.local/bin`.
- An ok for the proxied DNS record the tunnel creates.

Until then, the quick tunnel is the stopgap.

**Answer:**

### Q-A6 · Phase-0 acceptance: where, and on which devices

**Proposed:**
- I iterate through the dev tunnel.
- Phase 0 is accepted on the VPS at `swap.latentstate.dev`, wired to the **test**
  bot (no users yet, so nothing to break), once you give the DNS record, SSH and the
  go.
- The production bot is connected only at MVP acceptance, with your go, and the
  test data is wiped at that switch.
- From then on, if you want staging, the test bot moves to
  `swap-next.latentstate.dev`, as `~/phonyx-staging` does.

Please list the clients we can test on (iOS / Android / Desktop / Web). §13 asks
for iOS, Android and Desktop at every stage.

**Answer:**

### Q-A7 · Backup storage (§13; needed by mid phase 1, not phase 0)

§12 puts backups in phase 1, so the skeleton doesn't need the bucket.

**Proposed:**
- Cloudflare R2: S3 API, 10 GB free, and `latentstate.dev` is already in your
  Cloudflare account. It is also a different provider from OVH, so losing the host
  doesn't lose the backups.
- You generate the `age` key pair; only the public key goes on the server.
- This differs from phonyx's on-box, unencrypted backups (your Decision 4 there).
  Swap's spec asks for off-box and encrypted, and I'll follow the spec.

**Answer:**

### Q-A8 · `@telegram-apps/sdk-react` has a successor

The package named in §8 has had no release since 3.3.9 (2025-10-08). Its GitHub repo
now redirects to `Telegram-Mini-Apps/tma.js`, its sibling `init-data-node` is
deprecated in favour of `@tma.js/…`, and the docs call `@tma.js/sdk` 3.x the direct
successor. `@tma.js/sdk-react` 3.0.x is current (peer React 17–19), and 4.0 is a
release candidate. Neither package needs Telegram's `telegram-web-app.js` script,
because the bridge is built in, so the "no third-party scripts" rule holds.

**Proposed:** `@tma.js/sdk-react` 3.x, pinned. Move to 4.x once it is stable and has
passed a phone check.

**Answer:**

## B. Before phase 1 (MVP)

### Q-B1 · The state-machine diagram did not survive the export

Where the diagram should be, §5 shows «[embedded content: машина состояний сделки ·
6 основных состояний, 3 терминальных]». The §9 and §12 diagrams are missing too, but
their text is enough. Here is my reconstruction from scenario 7, FR-4.3–4.6 and the
"6 + 3":

| From | Action (who) | To |
|---|---|---|
| — | propose (proposer) | `proposed` |
| `proposed` | accept (acceptor) | `accepted` |
| `proposed` | decline (acceptor), withdraw (proposer) | `cancelled` |
| `proposed` | 48 h pass (the only timed transition) | `expired` |
| `accepted` | «Отправил» on leg 1 (its payer) | `leg1_sent` |
| `leg1_sent` | «Получил» on leg 1 (its payee) | `leg1_received` |
| `leg1_received` | «Отправил» on leg 2 (its payer) | `leg2_sent` |
| `leg2_sent` | «Получил» on leg 2 (its payee) | `settled` |
| `accepted` | cancel (either) | `cancelled` |
| `leg1_sent` … `leg2_sent` | cancel request (either), then approve (the other) | `cancelled`; a declined request changes nothing |
| `accepted` … `leg2_sent` | «Проблема» with a comment (either) | `disputed` |
| `disputed` | resolve as settled or cancelled (either), then confirm (the other) | `settled` / `cancelled` |

- The six main states are proposed, accepted, leg1_sent, leg1_received, leg2_sent
  and disputed. The three terminal states are settled, cancelled and expired.
- A pending cancel request is a field on the deal, not a state.
- The legs are strictly sequential. The second payer can press «Отправил» only after
  confirming «Получил» on leg 1. That is what choosing who sends first protects.

**Proposed:** this table, or send me the original diagram.

**Answer:**

### Q-B2 · The balance formula in §5 never returns to zero

§5 takes the legs A sent and B confirmed, minus the mirror, per currency. After
scenario 3 that leaves "A is +50 000 RUB and B is +1 100 GEL". That is neither
scenario 3's «баланс снова нулевой» nor scenario 4's «Б должен мне 1 100 GEL до 28
октября».

**Proposed:** the balance is the open obligations of unsettled deals.
- Once leg 1 is confirmed received, the counter-leg's amount, in its currency and
  with its due date, is a confirmed debt of the leg-2 payer.
- While leg 1 is sent but not yet confirmed, the same amount is conditional.
- Settled and cancelled deals contribute nothing.
- Disputed deals are listed separately as «в споре», with no reminders. That is what
  "frozen" means.
- Amounts are summed per counterparty and currency.

**Answer:**

### Q-B3 · What "manual rate" means in the MVP, and orders that want several currencies

§12 puts "fixed and manual" in the MVP, but §6.3 defines only fixed and source-based
rates. And `wants[]` can hold GEL and USD while `rate_spec` has a single base/quote
pair.

**Proposed (ADR-0004):**
- **Fixed:** one rate per wanted currency, typed the way the author thinks («1 GEL =
  29,20 RUB»).
- **Manual:** the order says "rate set per deal", with an optional markup and a label
  («NBG»). The proposer types the reference rate into the proposal, the app applies
  the markup, and the acceptor sees the value, label and time before accepting.
- In the MVP both kinds lock at the proposal. Choosing `lock_at` arrives with live
  sources in v1.
- The formula is `amount_want = amount_give × rate(give→want) × (1 + markup)`,
  rounded half-up to 2 decimals once, at the end.

**Answer:**

### Q-B4 · Rounding the counter-amount

Cash rarely changes hands in tetri: 50 000 RUB at 29,20 is 1 712,33 GEL.

**Proposed:** the proposer can tick «округлить до целых» to round the counter-amount
to the nearest whole unit. The deal then shows the effective rate beside the formula.
Without the tick, amounts are exact to 2 decimals.

**Answer:**

### Q-B5 · What `amount_min` means

**Proposed:**
- `amount_max` is the total the author has.
- `amount_min` is the smallest single deal they accept. "Exact" means min = max, so
  one deal takes everything.
- A proposal must be at least min and at most the remainder.
- When the remainder drops below min, the order becomes `fulfilled` (FR-2.3).

**Answer:**

### Q-B6 · Counter-proposal and quiet hours: §6 says MVP, §12 says later

FR-4.2 (counter-proposal) and the quiet hours in FR-7.2 sit in MVP sections. §12
lists counter-proposal under v1 and quiet hours under v2.

**Proposed:** follow §12. In the MVP a proposal can only be accepted or declined; to
change the terms, decline it and propose again. The MVP notification setting is
"mute new orders from this link".

**Answer:**

### Q-B7 · Reminders can't be edits of the previous message

§10 has reminders edit their previous message instead of sending a new one. But
Telegram has no push notification for an edited message, so the reminder would
arrive silently. And a bot can't delete a message older than 48 h, while repeats
are 3 days apart.

**Proposed:**
- Each reminder is a new message.
- The previous reminder for the same leg is deleted if it is younger than 48 h.
  Otherwise its button is removed, so only the latest reminder is live.
- Reminders go out at 10:00 in the recipient's time zone.

**Answer:**

### Q-B8 · Who sees recipient details in full

The kickoff says masked everywhere except to the leg's payer.

**Proposed:**
- The payee who typed them also sees them in full. It's their data, and otherwise a
  typo in grandmother's card number stays invisible.
- The payer sees them only once the deal is accepted. Someone who may still decline
  doesn't get a card number.
- Everyone else, every log line and every bot message gets the masked form
  (`•••• 5678`).

**Answer:**

### Q-B9 · Breaking a link while a proposal is pending

§3 says open deals stay until they close and no new ones can be proposed. §5 says
there are no automatic transitions except expiry.

**Proposed:**
- Breaking or blocking a link cancels that pair's *unaccepted* proposals, journaled
  as «отменено: связь разорвана». This follows from a user's action; it isn't a
  timer.
- Accepted deals run to the end.
- The pair's orders stop being visible at once.

**Answer:**

### Q-B10 · Deleting an account that has live deals

**Proposed:**
- Deletion is refused while the user has a deal anywhere from accepted to disputed
  («сначала завершите сделки»).
- Their pending proposals are cancelled, and their links and sessions are deleted.
- Their orders are closed and scrubbed rather than deleted, because the journal
  references them.
- The user row becomes «Удалённый участник». Their documents go after 30 days (§3),
  and the whole deletion completes within 24 h (§7).
- For the user agreement: deleted data stays in the encrypted backups until their
  30-day retention runs out.

**Answer:**

### Q-B11 · Users who have only pressed /start, and @username lookups

§3 creates the profile at the first Mini App launch, but FR-1.1 allows a request to
"someone who already started the bot".

**Proposed:**
- The user is created or refreshed on first contact of either kind, bot or Mini App.
- A lookup that finds no one says «не найден — отправьте ссылку-приглашение». That
  reveals whether a username uses Swap, which seems acceptable among acquaintances.

**Answer:**

### Q-B12 · The bot may not be allowed to message someone

Someone who opens an invite link (`?startapp=`) without ever pressing /start can't
receive messages from the bot until they allow it.

**Proposed:**
- At first launch the app asks once, through `requestWriteAccess`.
- If they refuse or block the bot, they get in-app notifications only, and the other
  side of their deals sees «уведомления выключены».

**Answer:**

### Q-B13 · A document sent to the bot before «Отправил»

FR-5.1 auto-attaches only to legs that are already sent or received, but people
often send the screenshot first.

**Proposed:**
- If the sender has exactly one leg waiting for their «Отправил», the bot offers a
  single button, «Отметить «Отправил» и прикрепить». It is still an explicit action.
- Otherwise the bot lists the candidate deals as buttons.
- An album of screenshots gets one question, not one per picture.

**Answer:**

### Q-B14 · Four tabs for nine screens

**Proposed:**
- The tabs are «Главная», «Сделки», «Балансы» and «Связи».
- The profile opens from the avatar in Home's header.
- The unread-event feed (FR-7.3) sits behind a bell beside the avatar. Its counter
  also shows on the «Главная» tab.

**Answer:**

### Q-B15 · The user agreement

§2 relies on an agreement that says Swap is not a payment service, takes no part in
settlement and guarantees nothing.

**Proposed:**
- I draft a short Russian agreement and privacy note from §2, §7 and the retention
  periods.
- It is shown once, at first launch, with «Принимаю».
- You approve the text before acceptance.

**Answer:**

### Q-B16 · Confirm the spec's own defaults (§13)

- Recipient details are deleted 30 days after the deal closes, and saved recipients
  are v2. So the MVP profile has no «сохранённые получатели», although §11 lists it.
- The proposer sends first by default. Scenarios 2–3 have the order's author send
  first, which is the other choice in the same field.
- Lifetimes: a proposal lasts 48 h, an invite 72 h. The 7-day cooldown after a
  refusal applies per pair, to invite links and @username requests alike.
- No English in the MVP. Every string is in a dictionary from the first commit, bot
  messages included.

**Proposed:** all four as written.

**Answer:**

### Q-B17 · Smaller defaults I'll apply unless you object (one answer covers the list)

- **Orders.**
  - Every order is "I give X, want Y", so `Order.side` is dropped.
  - There are no server-side drafts; the wizard keeps its state until
    «Опубликовать».
  - `available_until` is required, defaulting to 14 days after `available_from`.
    Dates are calendar dates in the author's time zone, and an order expires at the
    end of its last day.
  - Payout methods are a fixed set (карта, СБП, наличные, банковский перевод,
    другое) plus an optional free-text note.
- **Deals.**
  - The acceptor enters their recipient details while accepting. They are required
    for card, SBP and bank transfer, and optional for cash and other.
  - A leg is overdue from the day after its due date, in the payer's time zone. The
    time zone is detected from the device at first launch and can be edited.
- **Notifications.**
  - A deal note notifies the other side; FR-7.1 doesn't list notes.
  - Notifications go out within about 5 s rather than once a minute (§9). A
    one-minute delay feels broken when both people are in the chat at the same time
    (ADR-0005).
- **Links:** outstanding invites are listed under «Связи» with «Отозвать».
- **Monitoring:** phonyx's on-box probe (`deploy/probe.sh`, `PROBE_SITES`) can watch
  `swap.latentstate.dev` too. The external pinger from §9 is yours to pick, since it
  needs an account.

**Answer:**

## C. Later phases (no answer needed now)

### Q-C1 · Source for the RUB rate (§13, v1)

**Proposed:** CBR as the official rate, as the spec says. A market source comes only
if participants ask for it. Before v1 I'll check that cbr.ru answers from the OVH
address, and if it doesn't, use a mirror of CBR's data.

### Q-C2 · A deal made from a match suggestion (v1)

When both sides have orders (scenario 5), the deal should reduce both remainders, but
`Deal` has a single `order_id`.

**Proposed:** an optional `counter_order_id` on the deal, in v1.

### Q-C3 · Browser sign-in (v1) without Telegram's widget script

The Login Widget is normally a `<script>` from telegram.org, which the kickoff's "no
third-party scripts" rules out.

**Proposed:** the widget's redirect flow through `oauth.telegram.org`, which returns
signed user data to our page. No script is loaded. It needs `/setdomain` on the bot.
