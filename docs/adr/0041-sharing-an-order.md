# 0041. Sharing an order: the order in words and its link, which grants nothing

Status: Accepted · Date: 2026-11-17 · Spec: §2, §10 «Telegram: Mini App»; QUESTIONS O1; builds on ADR-0013, ADR-0028

## Context

The owner wants to send an order he made to someone in a Telegram chat (QUESTIONS O1).
ADR-0013 already gives each card a link, `t.me/peertopeerswapbot?startapp=order_<id>`,
and treats the id as an address only: the api decides who sees the card. ADR-0028 lets
the author set how far along chains of links the order is seen. Nothing is visible to
anyone with no chain of links to its author (§2, as amended by J2).

## Decision

**The author shares an open order** with the card's main button, «Поделиться заявкой». It
opens Telegram's share sheet (`shareURL`, ADR-0003), where the author picks the chat.
Where there is no share sheet, the same text and link go to the clipboard.

**The message is the order in words, then its link.** Laid out as its row is (N1), in the
author's language:

```
Отдаю 150 000 ₽ RUB · Россия
→ 5 136,99 ₾ GEL по 1 GEL = 29,20 RUB
→ ≈ 1 842,98 $ USD по рынку
Заявка № 17 в Swap
```

- The amounts are what remains and what it comes to in each currency. The api works them
  out, so `GET /orders/{id}` now prices its wanted currencies as lists do. «≈» marks the
  market's rate of the moment. A currency the market has no rate for shows alone.
- The order's note stays out: it may say where to pay (ADR-0021). The author can add words
  in the chat.

**The link grants nothing.** It opens the card for whoever the order's reach includes,
the same as from the bot or the feed. Anyone else gets the api's 404, which now reads
«Заявка не найдена или вам не видна». It still says nothing about whether the order
exists. To share with someone outside the reach, the author raises the reach, or invites
them first (ADR-0012).

**Only the author shares, and only while the order is open.** Someone else's open order
keeps «Предложить сделку» as its main action. Once over, an order has nothing to share.

## Consequences

- Sharing needs no new table, endpoint or bot message. The bot's buttons and a shared
  link reach a card the same way (ADR-0013).
- A forwarded message carries the order's words wherever it goes, as a message typed by
  hand would. The card itself stays within the reach.
- A card costs one more lookup of the market's table, which is kept ten minutes.

## Alternatives considered

- **A link that shows the order to whoever holds it.** A forwarded message would show the
  order, its author's name and photo included, to people with no chain of links to its
  author. That is a public order by another door, which §2 rules out.
- **A link that also invites.** A stranger would get a link request and the order in one
  tap. Two flows in one, with the invite's one-time and 72-hour rules. QUESTIONS O1 asks
  the owner whether he wants it.
- **A prepared inline message with an «Открыть» button** (`savePreparedInlineMessage` and
  `shareMessage`). A tidier card in the chat. But the api would call the Bot API on each
  share, through the VPS's own server (ADR-0008), and the bot would need inline mode. The
  plain link comes first; this can follow if it reads poorly.
- **Letting anyone who sees an order share it.** Its words would travel past the reach its
  author chose.
