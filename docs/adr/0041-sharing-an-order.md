# 0041. Sharing an order: the order in words, and a one-time invite that carries it

Status: Accepted · Date: 2026-11-17 · Spec: §2, §3, §10 «Telegram: Mini App»; QUESTIONS O1; amends ADR-0012, builds on ADR-0013 and ADR-0028

## Context

The owner wants to send an order he made to someone in a Telegram chat (QUESTIONS O1).
PR 1.40 shared the card's own link, `startapp=order_<id>` (ADR-0013). That link granted
nothing: it opened the card for those the order already reached, and anyone else read
«не найдена или вам не видна». The owner then asked for the link to invite strangers
too.

An order's id can't do that. It travels in the bot's buttons and reaches everyone the
order reaches. If it could start a link, anyone two handshakes away could link up with
the author without the author agreeing to it. An invite is the author's consent, so the
shared link has to be one (ADR-0012).

## Decision

**«Поделиться заявкой»** is the main button of its author's open order. Each press mints
a one-time invite that carries the order (`invites.order_id`, `POST
/orders/{id}/share`). Then it opens Telegram's share sheet with the order in words and
the invite's link, `t.me/peertopeerswapbot?start=inv_<token>`. Where there is no share
sheet, the text and the link go to the clipboard.

**The words.** The order is written out as its row is (N1), in the author's language:

```
Отдаю 150 000 ₽ RUB · Россия
→ 5 136,99 ₾ GEL по 1 GEL = 29,20 RUB
→ ≈ 1 842,98 $ USD по рынку
Заявка № 17 в Swap
```

- The api works out the amounts: `GET /orders/{id}` prices its wanted currencies as lists
  do. «≈» marks the market's rate of the moment, and a currency with no rate now shows
  alone.
- The order's note stays out, since it may say where to pay (ADR-0021).

**Opening the link** goes through the bot's /start, as any invite does, so the bot may
write to whoever opens it (Q-B12). What happens depends on who opens it:
- **Someone who already sees the order** gets «{name} делится с вами заявкой № N»,
  whose «Открыть» opens the order. No link request is made.
- **Anyone else** gets the invite's link request from the author, worded «{name}
  приглашает вас в Swap и делится заявкой № N». «Открыть» opens the request, which names
  the order. Accepting it leads straight to the order: they are now one handshake away,
  within any reach of 1 or more.
- **At reach 0, «Только выбранным»,** whoever opens the link also joins the order's
  list. The author chose to show it to them, and the author's card lists them by name.
  They still see it only while linked to the author.
- **Its author** opening it is told it is their own link, and spends nothing.
- **Once the order is over** (closed, filled, past its last day or deleted), the link is
  a plain invite.

**One use.** Once someone other than its author opens it, the link is spent, even when
it makes no request. Only that person can open it again, as with any invite. Someone else
opening a spent link reads that the invitation no longer works, and sees nothing. Shared
links count against the 10 outstanding invites (§7, ADR-0012). The «Связи» tab lists them
as «Заявка № N: ссылка действует до …», where the author can revoke one.

**Only the author shares, and only while the order is open.** Someone else's open order
keeps «Предложить сделку» as its main action.

**The share sheet opens after the api answers,** within the same press. Telegram's
documented gesture rule covers `openLink`, not `openTelegramLink`; the owner's phone
check confirms it on a real client.

## Consequences

- A stranger gets from a chat message to the order in two taps of their own, and the
  author's consent, the invite, is there all along.
- Nobody sees an order without a chain of links to its author (§2): the stranger sees it
  only once linked, and the request needs their consent.
- A forwarded message carries the order's words wherever it goes, as a typed message
  would. The link itself works once.
- Each press mints an invite, even if the share sheet is then closed. The invite expires
  in 72 hours, or the author revokes it in the «Связи» tab.
- The order's own `startapp=order_<id>` link (ADR-0013) is unchanged. It stays the bot's
  way into a card.

## Alternatives considered

- **The card's own link, granting nothing** (PR 1.40). It left a stranger at «не
  найдена», and the owner asked for more.
- **A link that shows the order to whoever holds it.** A forwarded message would show the
  order, its author's name and photo included, to people with no chain of links to its
  author. That is a public order by another door, which §2 rules out.
- **A reusable link per order.** One link for a group chat, but a forwarded one would
  keep making requests in the author's name. One use per press matches ADR-0012.
- **A prepared inline message with an «Открыть» button** (`savePreparedInlineMessage` and
  `shareMessage`). A tidier card in the chat, but the api would call the Bot API on each
  share through the VPS's own server (ADR-0008), and the bot would need inline mode.
- **Letting anyone who sees an order share it.** Its words would travel past the reach
  its author chose, and the invite would be in someone else's name.
