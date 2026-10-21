# 0013. Deep links: the bot's buttons open `startapp=<kind>_<id>`, and the app reads one start parameter

Status: Accepted · Date: 2026-10-22 · Spec: §10 «Telegram: Mini App», FR-7.1; Q-A1, Q-B12

## Context

Every bot notification carries «Открыть», which must open the right card (FR-7.1, §10).
Invites are a bot link instead (`?start=`, ADR-0012). The owner set the Main Mini App to
open fullscreen (Q-A1). The tma.js SDK reads launch parameters from the URL's query and
hash alike.

## Decision

- **A target is `<kind>_<id>`**: `link_<uuid>`, `order_<uuid>` or `deal_<uuid>`.
  Telegram allows up to 512 characters of `A-Za-z0-9_-` in a start parameter, so a
  uuid fits, hyphens and all.
- **The bot's «Открыть» is a URL button** to
  `https://t.me/peertopeerswapbot?startapp=<target>`. It opens the Main Mini App the
  way BotFather configures it, fullscreen, and Telegram signs the target into
  `initData` as `start_param`. The buttons are built in one helper.
- **The app reads `tgWebAppStartParam` once, at start.** A known target becomes the
  router's second entry, above Home, so BackButton leads Home. Anything else opens
  Home.
- **An id in a target is only an address.** The screen loads it through the api, which
  checks access as for any other request, so a stranger gets 404.
- The /start greeting and the menu button keep their `web_app` buttons, which open
  Home.
- **The fallback.** If a client mishandles `startapp` from a button, for example with a
  confirmation or the wrong screen, the bot switches to a `web_app` button whose URL
  carries `?tgWebAppStartParam=<target>`. The SDK reads that the same way, so only the
  helper changes.

## Consequences

- There is one way into a card, whether from the bot, a link shared by hand, or later
  the in-app feed.
- The owner's phone check of PR 1.1 covers `startapp` on a real client, which the spec
  lists as a risk (§13).

## Alternatives considered

- **Paths such as `/deals/<id>` behind a `web_app` button.** The api would serve them
  (ADR-0001), but the Mini App wouldn't open fullscreen, and the link couldn't be shared
  as a t.me link.
- **Routes in the URL's hash.** Telegram puts its launch parameters there.
