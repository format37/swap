# Questions for the owner

The owner answered parts A and B on 2026-10-21; each answer sits under its item.

Each item ends with a proposed default. **"ok" accepts it**; anything else replaces
it. Answer under **Answer:** or in the PR review. Once answered, an item is folded
into an ADR (or the code) and marked here with the date. Nothing is deleted.

- **Part A** blocks phase 0. If you only have a minute, answer A1–A6 and A8.
- **Part B** blocks phase 1 (MVP).
- **Part C** is for later phases and needs no answer now.
- **Part D** records the owner's own decisions of 2026-10-21.
- **Part E** was raised while planning phase 1. I follow its defaults until you answer.
- **Part F** records the owner's notes after his first test of slice 1, on 2026-10-22.
- **Part G** records his notes after the demo with others, the same day, and asks G7.
- **Part H** records his notes after the first real deal, the same day.
- **Part I** records the owner's Sentry setup, the same day.
- **Part J** records the owner's notes of that evening: the wizard, reach by handshakes,
  deleting, photos and the score. Its defaults are marked; I follow them until the owner
  says otherwise.
- **Part K** records the owner's priority list for the rest of phase 1, with its defaults.
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

**Answer (the owner, 2026-10-21):** use the production bot for everything; no test
bot for now. «Allow Groups» is off. The Main Mini App is on, fullscreen, at
`https://swap.latentstate.dev`. The owner logged the bot out of the cloud Bot API the
same day: it runs through the VPS's own Bot API server and relay, like gptaidbot.
→ ADR-0008.

### Q-A2 · GitHub repository

**Proposed:** a private `format37/swap`, like phonyx. I create it with `gh`, push
`main`, protect `main` (PR and green CI required), and open these docs as the first
PR.

**Answer:** public and open source: `github.com/format37/swap`, MIT licence.

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

**Answer:** ok, without breaking the other services. → ADR-0001, amended: the api
sets its own security headers, so the shared Caddyfile is edited only once.

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

**Answer:** ok. → ADR-0011: one session per launch, 24 h.

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

**Answer:** no tunnel. I test in desktop Chrome with mobile emulation, and the owner
tests in Telegram on the VPS. → ADR-0011.

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

**Answer:** accepted on the VPS, with the production bot (A1). The device list is
still to come; the owner tests in Telegram.

### Q-A7 · Backup storage (§13; needed by mid phase 1, not phase 0)

§12 puts backups in phase 1, so the skeleton doesn't need the bucket.

**Proposed:**
- Cloudflare R2: S3 API, 10 GB free, and `latentstate.dev` is already in your
  Cloudflare account. It is also a different provider from OVH, so losing the host
  doesn't lose the backups.
- You generate the `age` key pair; only the public key goes on the server.
- This differs from phonyx's on-box, unencrypted backups (your Decision 4 there).
  Swap's spec asks for off-box and encrypted, and I'll follow the spec.

**Answer:** ok (part of «agree with everything else»). Needed by slice 7.

### Q-A8 · `@telegram-apps/sdk-react` has a successor

The package named in §8 has had no release since 3.3.9 (2025-10-08). Its GitHub repo
now redirects to `Telegram-Mini-Apps/tma.js`, its sibling `init-data-node` is
deprecated in favour of `@tma.js/…`, and the docs call `@tma.js/sdk` 3.x the direct
successor. `@tma.js/sdk-react` 3.0.x is current (peer React 17–19), and 4.0 is a
release candidate. Neither package needs Telegram's `telegram-web-app.js` script,
because the bridge is built in, so the "no third-party scripts" rule holds.

**Proposed:** `@tma.js/sdk-react` 3.x, pinned. Move to 4.x once it is stable and has
passed a phone check.

**Answer:** ok.

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

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

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

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

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

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

### Q-B4 · Rounding the counter-amount

Cash rarely changes hands in tetri: 50 000 RUB at 29,20 is 1 712,33 GEL.

**Proposed:** the proposer can tick «округлить до целых» to round the counter-amount
to the nearest whole unit. The deal then shows the effective rate beside the formula.
Without the tick, amounts are exact to 2 decimals.

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

### Q-B5 · What `amount_min` means

**Proposed:**
- `amount_max` is the total the author has.
- `amount_min` is the smallest single deal they accept. "Exact" means min = max, so
  one deal takes everything.
- A proposal must be at least min and at most the remainder.
- When the remainder drops below min, the order becomes `fulfilled` (FR-2.3).

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

*Changed by F4 (2026-10-22): min may be 0, any amount.*

### Q-B6 · Counter-proposal and quiet hours: §6 says MVP, §12 says later

FR-4.2 (counter-proposal) and the quiet hours in FR-7.2 sit in MVP sections. §12
lists counter-proposal under v1 and quiet hours under v2.

**Proposed:** follow §12. In the MVP a proposal can only be accepted or declined; to
change the terms, decline it and propose again. The MVP notification setting is
"mute new orders from this link".

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

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

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

### Q-B8 · Who sees recipient details in full

The kickoff says masked everywhere except to the leg's payer.

**Proposed:**
- The payee who typed them also sees them in full. It's their data, and otherwise a
  typo in grandmother's card number stays invisible.
- The payer sees them only once the deal is accepted. Someone who may still decline
  doesn't get a card number.
- Everyone else, every log line and every bot message gets the masked form
  (`•••• 5678`).

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

### Q-B9 · Breaking a link while a proposal is pending

§3 says open deals stay until they close and no new ones can be proposed. §5 says
there are no automatic transitions except expiry.

**Proposed:**
- Breaking or blocking a link cancels that pair's *unaccepted* proposals, journaled
  as «отменено: связь разорвана». This follows from a user's action; it isn't a
  timer.
- Accepted deals run to the end.
- The pair's orders stop being visible at once.

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

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

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

### Q-B11 · Users who have only pressed /start, and @username lookups

§3 creates the profile at the first Mini App launch, but FR-1.1 allows a request to
"someone who already started the bot".

**Proposed:**
- The user is created or refreshed on first contact of either kind, bot or Mini App.
- A lookup that finds no one says «не найден — отправьте ссылку-приглашение». That
  reveals whether a username uses Swap, which seems acceptable among acquaintances.

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

### Q-B12 · The bot may not be allowed to message someone

Someone who opens an invite link (`?startapp=`) without ever pressing /start can't
receive messages from the bot until they allow it.

**Proposed:**
- At first launch the app asks once, through `requestWriteAccess`.
- If they refuse or block the bot, they get in-app notifications only, and the other
  side of their deals sees «уведомления выключены».

**Answer:** invitations go through the bot, `t.me/peertopeerswapbot?start=<token>`,
so everyone presses /start and the bot may write to them (the owner).
`requestWriteAccess` stays only as a fallback for someone who reaches the app another
way.

### Q-B13 · A document sent to the bot before «Отправил»

FR-5.1 auto-attaches only to legs that are already sent or received, but people
often send the screenshot first.

**Proposed:**
- If the sender has exactly one leg waiting for their «Отправил», the bot offers a
  single button, «Отметить «Отправил» и прикрепить». It is still an explicit action.
- Otherwise the bot lists the candidate deals as buttons.
- An album of screenshots gets one question, not one per picture.

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

### Q-B14 · Four tabs for nine screens

**Proposed:**
- The tabs are «Главная», «Сделки», «Балансы» and «Связи».
- The profile opens from the avatar in Home's header.
- The unread-event feed (FR-7.3) sits behind a bell beside the avatar. Its counter
  also shows on the «Главная» tab.

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

### Q-B15 · The user agreement

§2 relies on an agreement that says Swap is not a payment service, takes no part in
settlement and guarantees nothing.

**Proposed:**
- I draft a short Russian agreement and privacy note from §2, §7 and the retention
  periods.
- It is shown once, at first launch, with «Принимаю».
- You approve the text before acceptance.

**Answer:** ok (the owner, 2026-10-21: «agree with everything else»).

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

**Answer:** ok, with two changes from the owner. Saved payment details are in the MVP
(ADR-0010), though a deal's copy is still deleted 30 days after it closes. And the MVP
speaks Russian, English and Georgian, with a switch (ADR-0009).

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

**Answer:** ok. Payout methods gain «крипто», and the acceptor picks saved payment
details instead of typing them (ADR-0010).

*Changed by F3 (2026-10-22): `available_until` is optional, and empty by default.*

## C. Later phases (no answer needed now)

### Q-C1 · Source for the RUB rate (§13, v1)

**Proposed:** CBR as the official rate, as the spec says. A market source comes only
if participants ask for it. Before v1 I'll check that cbr.ru answers from the OVH
address, and if it doesn't, use a mirror of CBR's data.

*Answered by F5 (2026-10-22): a market outside Russia, not CBR.*

### Q-C2 · A deal made from a match suggestion (v1)

When both sides have orders (scenario 5), the deal should reduce both remainders, but
`Deal` has a single `order_id`.

**Proposed:** an optional `counter_order_id` on the deal, in v1.

### Q-C3 · Browser sign-in (v1) without Telegram's widget script

The Login Widget is normally a `<script>` from telegram.org, which the kickoff's "no
third-party scripts" rules out.

**Proposed:** the widget's redirect flow through `oauth.telegram.org`, which returns
signed user data to our page. No script is loaded. It needs `/setdomain` on the bot.

## D. Decided by the owner on 2026-10-21

These weren't questions of mine, but they change the plan, so they are recorded here
too.

- **A public, open-source repository** (A2), MIT.
- **The production bot from day one** (A1), through the VPS's Bot API server and relay
  (ADR-0008).
- **Russian, English and Georgian**, with a language switch (ADR-0009).
- **Saved payment details**: free text per asset, crypto included (ADR-0010).
- **Invitations through /start** (Q-B12).
- **Simple, native, readable without reading:** icons, symbols and flags carry the
  meaning (ADR-0003).
- **No overengineering.** The smallest thing that works, then iterate.

## E. Phase 1 (asked 2026-10-22)

Planning slice 1 raised these. I follow each default until you answer, and an answer
that changes one comes with a fix.

### Q-E1 · The 7-day cooldown and invite links

Q-B16 applies the cooldown "to invite links and @username requests alike". But an
invite can't be pushed at anyone: it becomes a request only when the invitee opens it
themselves.

**Proposed (ADR-0012):** after B declines A, A's requests to B's @username are refused
for 7 days. If B opens an invite from A during that time, that is B's own doing, so it
works and shows B the request again.

### Q-E2 · Proposals that an order can no longer cover

A remainder shrinks only when a deal is accepted (FR-2.3), so several proposals can
wait on one order at once. After one is accepted, the others may no longer fit. And an
order that closes leaves its proposals hanging until they expire after 48 h.

**Proposed:** a pending proposal is cancelled in the same transaction when:
- its order is closed by its author, used up, or expires;
- or an accepted deal shrinks the remainder below the proposal's amount.

It is journaled with the reason («заказ закрыт», «остатка не хватает»), and the
proposer is notified. Like Q-B9, it follows from someone's action or from the order's
own end date, so no new timer is involved.

### Q-E3 · The demo comes before the user agreement

The demo, after slice 1, is a real deal among your acquaintances. The agreement screen
(Q-B15) comes in slice 7.

**Proposed:** run the demo without it. The bot's greeting, which everyone sees at
/start (Q-B12), already says that Swap never holds or moves money. The agreement is in
place before acceptance, as planned.

## F. The owner's notes after his first test (2026-10-22)

The owner ran slice 1 on his own and sent seven notes. They are decisions, so each is
quoted, followed by what it changes. Where they differ from Q-B5, Q-B17 or Q-C1, they
win. ADR-0019 and ADR-0020 hold the details.

### F1 · «Отдаёте» instead of «Выберите»

> Когда я выбираю валюту, там написано Выберите и список валют. Я бы лучше вместо
> Выберете написал Отдаёте. Потому что рассеяный пользователь можть отвлечься и забыть
> какая это валюта - та что он отдаёт или та что получает.

The currency list opens with «Отдаёте» on step 1 and «Получаете» on step 2. → PR 1.8.

### F2 · How the author can be paid

> Как вы можете отдать я выбрал, но стоит сделать такой же селектор - как вы можете
> получить.

An order also says how its author can be paid, from the same six ways, on step 2. A
proposal pays in one of them. Orders published earlier take all six. → PR 1.9.

### F3 · The last day is optional

> Последний день я бы разрешил оставить незаполненным - по-умолчанию.

The last day is off by default, and such an order stays open until its author closes
it. Asking for one still suggests two weeks, as Q-B17 did. → PR 1.8.

### F4 · A minimum of 0

> Минимум за сделку я бы тоже разрешил ставить 0 - просто что бы не мучать
> пользователя выбором

The minimum may be 0, and an empty field means 0: any amount up to the remainder. An
order without a minimum is used up when nothing is left. → PR 1.8.

### F5 · The market rate, at once

> Курс сразу предлагать по курсу не-российской биржи - можно выбрать любую популярную,
> которая бесплатно отдаёт курс по API.

The wizard fills each rate in from Coinbase's public rates, with the source and time
beside it, and the author can change it. What is published is still a fixed rate
(ADR-0004). This answers Q-C1 too. → PR 1.10, ADR-0020.

### F6, F7 · Deleting and restoring closed orders

> Возможность удалять и / или архивировать / скрывать закрытые заявки

> Возвожность восстанавливать закрытые (не удаленные) заявки

The author can reopen an order they closed, as it was, and delete an order that is no
longer open. A deleted order is gone from every list and card, the author's included,
while its deals run to the end. Of delete, archive and hide, delete is built: next to
reopening, an archive would be a second home for the same orders. → PR 1.11.

## G. The owner's notes after the demo with others (2026-10-22)

The owner and two acquaintances tried slice 1 together. Links and an order worked, but
no proposal went through. He sent six notes and then a seventh. Like part F, they are
decisions; where they differ from Q-B3, Q-B8 or part F, they win. ADR-0021 and ADR-0022
hold the details.

### G1 · Narrower choices when taking an order, and no name and details

> Когда пользователь соглашается на сделку - он выбирает валюту которую он будет
> отдавать - выбор нужно сузить из того что предлагает сделка изначально. Список валют,
> список способов оплаты. И не нужно требовать указать name and details.

The proposal already offers only the order's currencies and ways (F2). What offered
everything was «Add payment details», which the proposal sent people to: of four entries
saved that day, two are in AMD and EUR, for an order in RUB. With G3, payment details
leave deals: neither the proposal nor accepting asks for them. → PR 1.12.

### G2 · The market rate by default

> Когда моя заявка висит и видна другим пользователям - пусть по умолчанию она висит с
> динамическим курсом если я не зафиксировал его при создании. то есть каждый раз когда
> кто то видит заявку, курс подтягивается с API.

An order follows the market (Coinbase, ADR-0020) unless its author fixes the rate on
step 2. Whoever opens it sees the rate of the moment, and a proposal locks the rate it
was made at (Q-B3). → PR 1.15, ADR-0022.

### G3 · Only what the exchange needs

> В целом хорошо было бы упростить интерфейс там где это разумно. Например, Add payment
> details и вовсе не нужен. Выбрали из доступных и все. Впринципе, даже какой банк не
> так важно. Об этом можно написать в комментарии при желании. Задача приложения
> спланировать обмен. А детали - они уже сами разберут. Важно только какая валюта на
> какую меняется, сумма, срок, способ обмена - нал, банк или крипта

- No payment details anywhere. The profile loses «Реквизиты», and a deal shows no
  account numbers. The proposal gets an optional comment for the rest, such as which
  bank. → PR 1.12.
- Three ways: cash, bank and crypto. Card, SBP and «other» become bank, in orders and
  deals alike. → PR 1.13.

### G4 · The whole amount by default

> Amount пусть будет full by default (если еще не. мне показалось он 0, но я не уверен)

It wasn't: the field was empty, with a grey 0 in it. A proposal now starts at all that
remains. → PR 1.12.

### G5 · «Send proposal» did nothing

> И главное, принять заявку у @menshikov_av так и не получилось. Send proposal - no
> reaction.

> the issue maybe was in requirement of choosing the payment type which was buggy - not
> chosen after each submit click

No proposal reached the api that day. The form stopped itself, and said why in a line at
the foot of a long page, out of sight. The likeliest reason was the payment details it
required (G1). Every form now keeps what stops it in sight, just above the main button.
→ PR 1.12.

### G6 · No way on from a link's screen

> После приглашения, если снова нажать по кнопке Open пользователь снова попадает на
> страницу приглашения. Но совсем не очевидно что надо нажать на back в левом верхнем
> углу - что сбивает пользователя с толку и он не знает что делать дальше.

The bot's «Открыть» leads to the link's screen, which offers only «Разорвать» once the
link is made. It now has a main button to Home. → PR 1.14.

### G7 · The payment details already saved (asked 2026-10-22)

Four entries were saved before G3. They are sealed with the key on the VPS, and since
PR 1.12 nothing in the app reads them.

**Proposed:** delete them in slice 2, with their table, their api and the key. They stay
until you answer, because deleting them can't be undone.

**Answer:** yes (the owner, 2026-10-22: «Да, можно удалять»). Done in PR 1.16, without
waiting for slice 2: migration 0013 drops the table, the code that sealed them goes, and
`RECIPIENT_KEYS` leaves the server's `.env`.

## H. The owner's notes after the first real deal (2026-10-22)

@format37 and irinayurasova ran a deal to «Получил» on both sides. The owner then sent
four notes. Like parts F and G, they are decisions; where they differ from Q-B1, Q-B7 or
Q-B16, they win. ADR-0023 and ADR-0024 hold the details.

### H1 · No «who goes first» and no dates

> Давай уберем опции:
> * Кто отправляет первым
> * Когда (срок перевода)

The proposal asks neither. Legs have no order and no due dates, and Q-B16's default
(the proposer first) goes with them. → PR 1.18.

### H2 · Both buttons at once

> По сути у нас оба участника должны и отправить и получить средства.
> Так что я бы обоим поставил кнопку подтверждения отправки и кнопку подтверждения
> получения
> […]
> По сути обе кнопки уже есть у каждого участника, но сейчас они разделены в очереди. А
> я предлагаю сделать обе кнопки доступны сразу, что бы участники сами решали кто и
> когда отправит и подтверждали по мере получения.

Once a deal is accepted, each side can mark «Отправил» on what they pay and «Получил» on
what they get, in any order. The deal settles when both receipts are marked. This
replaces Q-B1's strict order of legs. → PR 1.18, ADR-0024.

### H3 · The journal says what moved

> Очень удобно что есть лог. в него можно и записать какая валюта и в какой стране была
> отправлена
> какая валюта и в какой стране была получена - указывать это не нужно. программа это и
> так знает из параметров сделки

Each «отправлено» and «получено» line in the deal's journal names the amount, the
currency and the country, taken from the leg. Nobody types them. → PR 1.18.

### H4 · Past orders stay

> @format37 после завершения сделки вышел из неё нажав back и получил сообщение Не
> получилось заявка не найдена. Я понмиаю что она видимо ушла в архив или в историю или
> удалилась - но я бы хранил заявки прошлого для истории. Это помогает нам вспоминать что
> мы делали раньше. Для учета расходов например. Ну и базово это выглядит как ошибка. У
> irinayurasova жта заявка в списке как исполнена. можно их все поместить в foldable
> группу исполненные, или на отдельную страницу

Whoever had a deal on an order can still open it after it ends, though not propose on it
again. Home folds finished orders, the author's own and those one dealt on, under
«Завершённые заявки». An order's card lists its finished deals too. → PR 1.17,
ADR-0023.

## I. Error reports (2026-10-22)

### I1 · Sentry now, in one project

The owner set Sentry up in phase 1, ahead of v1, from Sentry's own onboarding: one new
project for Swap, apart from Phonyx's, and only production. On what to send he took
errors and tracing with no personal data. → ADR-0025.


## J. The owner's notes on slice 1, the evening of 2026-10-22

The owner sent five notes in two messages. Like parts F–H, they are decisions. Where they
differ from §2, §3, §5, Q-B10, ADR-0003, ADR-0004, ADR-0016, ADR-0019 or ADR-0022, they
win. Where a detail was left open, the item marked **Default** stands until the owner
says otherwise. ADRs 0026–0030 hold the details.

### J1 · The wizard in two steps

> Предлагаю упростить дизайн создания новой заявки:
> * Шаг 1 включает в себя сразу и Отдаёте и Получаете. Отдаёте: Валюта, сумма, флаг
>   только целиком, минимум за сделку, как вы моджете отдать, когда, ограничить срок.
>   Убираем заголовки, стакаем все в группу под заголовком "Отдаёте". Получаете
>   аналогично: Валюта, курс, еще валюта, флаг фиксировать курс для каждой (выключен
>   по-умолчанию), как получать. Следующий шаг дайджест в заголовке, выбор кому видно,
>   комментарий.

> Насчет страны согласен - оставляем, особенно когда речь идет о наличке.

- **Two steps** instead of three.
- **Step 1** has two groups, «Отдаёте» and «Получаете», with no section titles inside
  them. Each row keeps its own label.
  - «Отдаёте»: currency, country, amount, «Только целиком», «Минимум за сделку», «Как вы
    можете отдать», «Когда», «Ограничить срок».
  - «Получаете»: each currency with its country, its rate and its own «Зафиксировать
    курс», off by default; «Ещё валюта», up to three; «Как получать».
- **Step 2** opens with a digest of step 1, such as «Отдаёте 150 000 RUB · Россия → GEL
  по рынку или USD по 1 USD = 80 RUB». Then come «Кому видно» (J2's slider) and the
  comment.
- **The country stays.** It is prefilled from the currency, and it matters most for cash.

**Default:** the live preview «Отдав …, получите ≈ …» stays under each wanted currency.

A switch per currency means each wanted currency carries its own rate, fixed or the
market's, so the rate moves from the order to its currencies. → PR 1.20, ADR-0026.

### J2 · Reach by handshakes

> Насчёт "Всем моим связям" - я бы сделал опцию: количество рукопожатий от 0 до
> бесконечности слайдером на несколько позиций, с визуализацией графа с иконками и
> именами.

> На бесконечности не увидят все. Человек и последующая цепочка может быть приглашен по
> инвайту а потом связь может быть разорвана и тогда образуется два независимых острова,
> которые друг до друга не достучатся. Понимаю что шанс не велик, однако при потере
> доверия это может происодить.
> […]
> 0 рукопожатий это только люди из списка. 1 рукопожатие это текущие связи как сейчас.
> Когда человек смотрит на список доступных заявок - у него есть фильтр который
> бесконечность рукопожатий по умолчанию, он может поставить от 0 до бесконечности. где 1
> это текущие связи. Зачем ноль? Что бы отфильтровать по избранным. Пока этого нет -
> давай сделаем фильтр видимости от 1 до бесконечности рукопожатий, бесконечность
> по-умолчанию.
> Я пока не вижу причин делать сущность круга друзей. Есть пользователь. у него есть
> прямые связи одного рукопожатия. А насколько рукопожатий вдаль он виден другим - он
> настраивает сам.
> Жаль чтьо эта концепция не очевидна - по этому я предлагаю сделать её в некотором
> состоянии по-умолчанию без возможности сломать механику. Если считаешь что это лишнее
> усложнение усложняющее жизнь пользователя - скажи.

- **Distance** counts handshakes over active links. 1 is the author's own links, 2 is
  their links, and so on. ∞ is everyone the author reaches through chains of active
  links. A broken link can split the network into islands that never see each other.
- **The author's reach** is set per order, on the wizard's step 2. It is a slider with
  stops 0, 1, 2, 3 and ∞, and it replaces the two radio buttons.
  - 0 is «Только выбранным»: people the author picks from their own links.
  - 1 is what «Всем моим связям» meant until now.
- **The viewer's filter** on «Открытые мне» has stops 1, 2, 3 and ∞, with ∞ by default.
  Its 0, favourites, waits until favourites exist («Потенциальные планы» in plan.md).
- **No circles of friends and no groups.** There is a person, their direct links, and
  the reach they set.
- **Who sees an order:** it is open, the viewer is within its reach (or on its list, at
  0), and the viewer is within their own filter. The author always sees it.
- **Policy.** This overrides §3 («Связь не транзитивна», «никто не видит чужих связей»)
  and CLAUDE.md's rule that visibility is active links only. Visibility now follows
  chains of active links, up to the author's reach. What stays:
  - no escrow;
  - no money moved;
  - nothing visible to anyone with no chain of links to the author.

**The owner's question, and the answer given (2026-10-22).** Handshakes are not a
needless complication. Under the hood it is one number per order and one filter, and
only the word can confuse. So:
- **Words on the slider.** Its stops read «Только выбранным», «Мои связи», 2, 3 and «Вся
  сеть». Under it stands who will see the order: «4 ваших связи и ещё 11 человек».
- **A folded filter.** The feed's filter stays folded, at «Вся сеть».
- **No broken state.** «Только выбранным» needs at least one person.

**Defaults:**
- **New orders reach 2,** «мои связи и их связи», not ∞.
  - A newcomer's name, photo and amount then reach no one five acquaintances away until
    the newcomer moves the slider.
  - The viewer's filter is ∞, as the owner said. It only narrows what the reach allows.
  - Existing orders keep what they have: 1 without a list, 0 with one.
- **The picture is rings, not a web of lines.** The author sits in the middle, with a
  ring per handshake and avatars with names on each. A web of lines stops being readable
  on a phone at about fifteen people. It is plain SVG, with no library (the 300 KB
  budget).
- **Anyone who sees an order may propose on it,** without a direct link first, because
  the author chose the reach.
  - The card shows the chain («через Нино → Гиорги») and the author's score (J5).
  - This overrides §5's «Создаётся только между сторонами с активной связью».
- **The bot announces a new order to direct links only.** People in farther rings find
  it in the feed.
- **A deal outlives a broken chain.** Once proposed, it stays visible to both sides, as
  a deal does when a link breaks.

→ PR 1.22, ADR-0028.

### J3 · Each side deletes for themselves

> Создатель может удалить заявку. Я думаю дать право удалять заявку в одностороннем
> орядке каждому участнику сделки - ему это может быть полезно в целях безопасности. С
> возможностью восстановить по запросу к тому кто её еще не удалил. То есть с функцией
> поделиться сделкой но только среди участников.

> 3. Насчет шейринга удаленной сделки - давай все таки не будем заморачиваться - не хочу
> усложнять. удалил - сам виноват. попросит скрин если что. убираем этот пункт.
> […]
> Да, удалять можно только завершенную сделку. Сделка может быть погашена частично. В
> таком случае приглашенный участник сделки может удалить свою часть но только у себя.
> Владелец сделки может удалить только всю сделку целиком, только когда закроет её и
> опять же только у себя.
>
> Когда все у себя удалили - можно удалять с сервера.
>
> Ок - сообщения в чате останутся. Пользователь может удалить сам если нужно.

Here «сделка» means the whole order. Its «владелец» is the author, and a «приглашённый
участник» is someone who took a part of it.

- **Only for oneself, and only what's finished.**
- **A participant** deletes their own deal once it's over, even while the order is still
  open. Over means settled, cancelled, declined, withdrawn or expired.
- **The author** deletes only the whole order with all its deals. That works only once
  the order is no longer open and none of its deals still runs.
- **No way back.** There is no restore and no sharing back: «удалил - сам виноват». The
  other side can send a screenshot.
- **The server erases what everyone has deleted.**
  - A deal goes when both its sides have deleted it.
  - An order goes when its author has deleted it and none of its deals remain.
  - Legs, journal lines and notifications go with them.
- **Chat messages stay.** The bot's messages remain in each person's chat, and people
  delete those themselves.

Until now (PR 1.11, F6) only the author deleted, and a deleted order vanished for
everyone, including those who dealt on it. Orders deleted that way keep their author's
deletion, and their participants see them in their history again. → PR 1.24, ADR-0030.

### J4 · Photo, name and @username

> Когда взаимодействуем с пользователями, например выбираем "Только выбранным" -
> подставлять лого пользователя.

> Фото не вместо инициалов. Хорошо было бы показывать и аватар и никнейм и указанное
> имя. Я понимаю что все это будет сложно уместить вместе, но можно например ник под
> именем оба справа от аватара. Кстати возможно фото и не придется хранить на сервере.
> Возможно оно уже есть доступное на серверах телеграм по ссылке.

- **One layout for a person.** The avatar sits on the left; to its right is the name,
  with the @username under it.
- **It goes everywhere a person is shown:** «Только выбранным» first, then links,
  requests, orders, deals, the profile, and J2's rings. Inline text (the journal, «payer →
  payee») keeps the name alone.
- **The avatar** is the Telegram photo, or initials when there is none.
- **Only a link is stored**, when Telegram provides one. The photo loads straight from
  Telegram.

→ PR 1.21, ADR-0027.

### J5 · The score

> Кстати насчет доверия, я хочу вести учет успешных сделок - назовем это скором. При чем
> не больше одного балла на пользователя, что бы они не могли друг другу накручивать
> скор.

A person's score is the number of different people they have a settled deal with.
Repeat deals with the same person add nothing.

**Defaults:**
- **Where it shows.** In the person's block next to the name, wherever a person is shown.
  A tap explains it: «Успешные сделки с 7 разными людьми».
- **How it's counted.** From the settled deals still on the server. A deal that both
  sides deleted (J3) takes its point with it. Keeping points apart from deals would keep
  who dealt with whom after both asked to erase it.
- **A known limit.** It doesn't stop someone with several Telegram accounts. In a network
  that grows only by invitation, that limit is accepted.
- **Policy.** §2 lists reputation beyond personal links among what Swap doesn't do, and
  CLAUDE.md said "no reputation". The owner's decision overrides both.

→ PR 1.23, ADR-0029.

## K. The owner's priority list (2026-10-22)

> По следующим слайсам приоритет:
> * Настройка уведомлений. Отключить все уведомления, уведомлять по типам сделок. и др.
> * Удаление аккаунта, удаление всей истории сделок одной кнопкой в настройках
> * соглашение, share to me the privacy policy url
> * Экспорт всех сделок где пользователь учавствовал в CSV
> * Sentry
> * Переключение языков интерфейса
> * Флаг создать авто заявку каждого N числа
> * Идентификатор у каждой заявки
> * contact to developer: email format37@gmail.com
>
> Остальное переносим в потенциальные планы и пока не реализуем.

They are built in this order after part J; K8 moves before K4, whose CSV needs it.
CSV export and Sentry come from v1, and recurring orders from v2. The owner pulled them
forward, which overrides §12's phases for them. Everything else moves to «Потенциальные
планы» in plan.md and isn't built for now.

### K1 · Notification settings

- **The settings** gather on the profile screen behind Home's avatar, with a screen of
  their own where a list grows long. They hold K1, K2, K3's links, K4, K6 and K9.
- **«Все уведомления»** turns everything off at once. Then comes a switch per kind of
  event. **Default** reading of «по типам сделок»:
  - new orders;
  - links;
  - proposals and answers;
  - transfers;
  - cancellations and disputes.
- **«и др.» Default:** muting one person's new orders (FR-7.2), on that link's screen.
  Quiet hours stay in «Потенциальные планы».
- **The outbox** drops whatever the recipient switched off.

→ PR 1.25.

### K2 · Deleting all history, and the account

- **«Удалить всю историю»** applies J3 to everything finished at once. What still runs
  stays, and the screen says how much.
- **«Удалить аккаунт»** follows Q-B10:
  - refused while a deal runs;
  - proposals cancelled;
  - links and sessions deleted;
  - the user becomes «Удалённый участник» within 24 h.

  With J3, everything finished counts as deleted by them, so whatever the other side has
  deleted too is erased.

→ PR 1.26.

### K3 · The agreement and the privacy policy

- **The agreement (Q-B15).** A short agreement and privacy note in ru, en and ka, shown
  once at first launch with «Принимаю». **Default:** it ships as drafted, and the owner
  approves the text later.
- **A public page** at https://swap.latentstate.dev/privacy. It opens in a plain browser,
  without the app's «Откройте через Telegram» stub. Its URL goes to the owner in the
  session, for BotFather.
- **What it says:**
  - what is stored, and for how long;
  - who sees what: J2's reach, J4's photos and J5's score;
  - how deletion works (J3, K2);
  - the deploy-time dumps kept on the same server;
  - error reports to Sentry (part I);
  - the contact (K9).

→ PR 1.27.

### K4 · CSV export

Every deal the user took part in (FR-6.3), one row each:
- the dates;
- the order's number (K8);
- the counterpart;
- what was given and what was received: amount, currency, country and way;
- the rate and its source;
- the status.

**Default:** the bot sends the file to the user's chat through the VPS's Bot API server.
A download inside Telegram's WebView is unreliable; `WebApp.downloadFile` is the
alternative. → PR 1.29.

### K5 · Sentry

Done before the list arrived: PR 1.19, part I, ADR-0025. The owner's setup bundles
Sentry's browser SDK and names the DSN's host in the CSP, so nothing goes through the
api. Readable Mini App stack traces (source maps) stay on the plan as PR 1.19's
follow-up.

### K6 · Switching the interface language

It has existed since phase 0 (Home's avatar → Профиль → Язык), and the bot follows it.
**Default:** a «Язык» row in the settings, with K1. **Asked:** what did the owner find
missing? An answer may add to it. → PR 1.25.

### K7 · Recurring orders

The wizard gains «Повторять каждый месяц, N-го числа».
- **The copy.** On day N, or the last day of a shorter month, the worker publishes a copy
  with a new number. It is published and announced like any new order.
- **The rate.** A fixed rate stays fixed; the market's follows the market.
- **Stopping.** «Больше не повторять» on any copy ends the series.
- **The job** is idempotent and survives restarts (ADR-0005).

→ PR 1.30.

### K8 · An order number

«№ 17», from one sequence for all orders. It shows on cards, rows and deals, in bot
messages, and in the CSV. → PR 1.28, before K4.

### K9 · Contacting the developer

format37@gmail.com, as the owner wrote it.
- A row in the settings with «Скопировать», because `mailto:` may not open inside
  Telegram.
- A line on the privacy page.

→ PR 1.27, with K3.

### K10 · When phase 1 is accepted

§12's acceptance leaned on features that now wait in «Потенциальные планы»: a document
through the bot, a balance, a backup restored into a clean container.

**Default:** phase 1 is accepted when parts J and K are live and the owner confirms. The
rest of §12's checklist moves to «Потенциальные планы» with the features it needs.

**Flagged to the owner (2026-10-22):** without off-box backups, the only copies are the
deploy-time dumps, the last five, on the same VPS. They survive a bad migration, not a
lost server.
