# 0012. Links: one pending request, whether it came by invite or by @username

Status: Accepted · Date: 2026-10-22 · Spec: §3, FR-1.1–1.5, §7; Q-B9, Q-B11, Q-B12, Q-B16, Q-E1

## Context

§3 gives two ways to link: an invite link, and a request to someone's @username. Either
way, the second side sees the inviter's name, @username and number of mutual links,
then presses «Установить связь» or «Отклонить» (FR-1.2). Invites go through the bot
(`?start=`), so every invitee has pressed /start and the bot may write to them (Q-B12).
ADR-0002 fixed one `links` row per pair and an `invites` table.

## Decision

**Both ways end in the same pending request**: the pair's `links` row with
`status = pending`, and `requested_by` set to the inviter or the requester. The other
side answers it on one screen, whichever way it came.

**An invite is a one-time bearer link**, `t.me/peertopeerswapbot?start=inv_<token>`.
- The token is 128 random bits in base64url. Only its SHA-256 is stored, as with
  sessions. So the app can't show a link again: the inviter shares it at once,
  through Telegram's share sheet or the clipboard, and revokes and replaces a lost
  one.
- It lives 72 h (Q-B16). A person has at most 10 outstanding at once, which is the
  rate limit §7 asks for.
- Pressing /start with it spends it. It becomes a pending request from the inviter to
  whoever pressed. The bot answers with the inviter's name and «Открыть», which opens
  that request (ADR-0013). Whoever opens a link first gets it: the inviter sees who
  among the sent requests and can withdraw.
- A link that can't make a request isn't spent: the inviter's own link, or a pair
  that is already linked. The bot says which.
- An expired, revoked or spent link gets a request for a new one.

**A request to an @username** finds the user by `lower(username)`. If there is nobody,
the code is `user.not_found`, and the app suggests an invite instead (Q-B11).

**When both have asked, they are linked.** A request or an invite towards someone who
has already asked you makes the link active at once, because both have consented.

**States.**
- `pending` → `active` when the receiver accepts, `declined` when they decline, and
  `removed` when the requester withdraws.
- `active` → `removed` when either side breaks it.
- `declined` and `removed` → `pending` again on a new request, which reuses the pair's
  row.
- `blocked` arrives with blocks in slice 6.

**The cooldown** (FR-1.2, Q-B16, Q-E1). For 7 days after B declines A, A's requests to
B's @username are refused with `link.cooldown`. If B opens an invite from A meanwhile,
that is B's own doing, and it works.

**Who is told what.** The receiver of a request is notified, and the requester is
notified once the link is established (ADR-0014). A decline, a withdrawal or a break
notifies nobody; the request just leaves the lists.

**Mutual links.** The request screen shows how many people are actively linked to both,
never who they are (§3: nobody sees anyone else's links).

**Authorization.** Only the two people of a pair can see or act on its row. Anyone else
gets 404, the same as for a row that doesn't exist. The receiver answers a pending
request, the requester withdraws it, and either side breaks an active link. Any other
action gets `link.invalid_state`.

**Breaking a link** hides the pair's orders at once, because visibility is a query over
active links. Cancelling the pair's pending proposals (Q-B9) arrives with deals.

## Consequences

- One screen and one code path answer both kinds of request.
- A forwarded invite can be claimed by the wrong person, as with any bearer link. The
  inviter sees who and can withdraw.
- The pair keeps one row through breaks and new requests. Its history isn't journaled,
  because `events` is for orders and deals (ADR-0002).

## Alternatives considered

- **An invite as a Mini App link (`?startapp=inv_…`)**, the spec's first sketch.
  Nobody presses /start, so the bot may not write to the invitee (Q-B12).
- **Accept and decline buttons in the bot's message.** A second place for the same
  decision, and a button in a chat goes stale once the request changes.
- **Keeping the token in the clear**, so the app can show the link again. Then a read
  of the database hands out working invites.
