# 0006. MVP build order: vertical slices, link + order + deal first

Status: Proposed · Date: 2026-10-21 · Spec: §11, §12 «Этап 1», §13 row 6; kickoff step 4

## Context

The first demonstrable slice is fixed: link + order + deal, without documents, on the
test bot (kickoff step 4, §13). Everything else in phase 1 depends on two
foundations. One is the trust boundary: who can see what, decided by links. The other
is the deal state machine. Kickoff rule 6 makes their tests mandatory, with negative
authorization tests written first.

## Decision

Each step is one or more PRs. Each PR carries its API, UI and tests, and is usable on
the test bot when merged.

**Slice 1, the demo (shown to the owner before anything else is built).**
1. **Links.** Create an invite link. The accept screen shows the inviter's name,
   @username and mutual links, with «Установить связь» / «Отклонить». Request a link
   by @username, list links, break a link.
2. **Orders.** The three-step wizard with a fixed rate only, the order card, and the
   Home feed: «открытые мне» and «мои». Visibility comes first, including the
   negative tests for "not linked" and "not in the order's list".
3. **Deals.** A proposal with amount, counter currency, who goes first, due dates and
   encrypted recipient details. The deal card with both legs and a status line that
   says what to do next. Accept, decline, withdraw, Sent and Received on each leg,
   settled, and cancel before the first Sent. The backend state machine is finished
   here, with every transition and every illegal one tested, including the cancel
   request and the dispute, whose screens come in slice 4.
4. **Bot notifications** for the events above, each with an «Открыть» button that
   opens the right card.

The demo is scenarios 1–3 on the test bot, minus the screenshot.

**Then, in order:**

| Slice | Content | Spec |
|---|---|---|
| 2 | Balances; deals list (active / history); the «требует моего действия» block on Home | FR-6.1, FR-6.3 (no CSV), §11 |
| 3 | Documents through the bot: auto-attach or ask, limits, MIME check by content, signed links | FR-5.1, 5.3–5.5 |
| 4 | Cancel request, dispute and resolve, deal notes | FR-4.5–4.7 |
| 5 | Reminders, order and proposal expiry, the in-app event feed with its counter, muting new orders from a link | FR-2.6, 4.4, 6.2, 7.2–7.3 |
| 6 | Manual rate; profile (name, time zone, default currencies); block and the block list; account deletion | §12 manual rate, FR-1.4, §3 |
| 7 | Encrypted off-box backups and a restore drill on a clean container; production hardening; the user agreement screen | §7, §9, §12 acceptance |

Acceptance runs with the owner and three acquaintances once slice 7 is in. Phase-1
acceptance checklist items map to slices: links 1, visibility 1, documents 3,
balances 2, state-machine tests 1, backup restore 7.

## Consequences

- The riskiest unknowns land first: visibility, the state machine, and Telegram's
  launch, notification and deep-link behaviour on real phones. Fixing them in slice 1
  is cheap; fixing them after slice 5 is not.
- Balances come right after the demo because they read the legs that slice 1 creates,
  and the owner will want to see "who owes whom" as soon as a deal exists.
- Documents wait for slice 3 because they need a leg in Sent and the bot's file
  handling, and they are kept out of the demo on purpose.
- The manual rate comes late because it is a variant of the fixed path. Its
  definition (Q-B3) may still change.

## Alternatives considered

- **Backend first, then all screens.** The demo would slip by several sessions, and
  UI problems with MainButton, BackButton and the WebView would surface late.
- **Following the §11 screen table top to bottom.** The table puts Home first, but
  Home is mostly a view over links, orders and deals, so it is assembled as they
  arrive.
