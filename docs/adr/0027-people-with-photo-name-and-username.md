# 0027. People are shown with their Telegram photo, name and @username

Status: Accepted · Date: 2026-10-22 · Spec: §7 «Приватность», §11; QUESTIONS J4; amends ADR-0003

## Context

`frontend/src/ui/Avatar.tsx` draws initials. ADR-0003 chose initials so that no
third-party image ever loads, and the CSP allows only `img-src 'self' data: blob:`
(`backend/swap/api/headers.py`). Screens show a person in several ways: a name alone, a
name with initials, or a name above an @username.

The owner asked for the user's photo where people are picked, as in «Только выбранным»,
and then everywhere, beside the name and the @username. The owner also suggested not
storing the photo if Telegram already serves it by link (J4).

Telegram puts a `photo_url` in the user object of `initData`, signed with the rest. It is
optional: it comes when the user's privacy settings allow it. It points at Telegram's own
host, as in `https://t.me/i/userpic/320/<id>.svg`, and the picture is a JPEG or an SVG.

## Decision

**Only the link is stored.**
- `users.photo_url` is taken from `initData` at every sign-in. When `initData` has none,
  the column is cleared, so a removed photo goes too.
- Only an `https://t.me/` URL is kept. Anything else is dropped, so the column can't
  point a browser elsewhere.
- The bot's /start carries no photo and leaves the column alone.

**The picture loads straight from Telegram.** The CSP's `img-src` gains `https://t.me`
and `https://*.telesco.pe`, and nothing else. `t.me` answers a userpic with a 302 to
Telegram's CDN, `cdn4.telesco.pe` and its siblings, and a CSP checks where a redirect
leads too (checked with curl on 2026-10-22). After the deploy, I check the host in the
stored URLs and count the users who have one.
- If none comes, initials stay.
- A copy through the bot is a follow-up to offer, not one to build unasked. It would
  call `getUserProfilePhotos` on the VPS's Bot API server, never api.telegram.org. And it
  would never hand out a Bot API file link: those carry the token.

**One `Person` component.**
- The avatar sits on the left; to its right is the name, with the @username under it.
  With ADR-0029, the score sits beside the name.
- The avatar is the photo, or the initials when there is none or it fails to load.
- It goes everywhere a person is shown: «Только выбранным» first, then links, requests,
  orders, deals, the profile, and the rings (ADR-0028). Inline text keeps the name
  alone, as in the journal and «payer → payee».
- The api's `Person` gains `photo_url`.

**Testing.** `dev_launch --photo <url>` puts a photo into the signed `initData`, so
Chrome shows the same thing a phone does.

## Consequences

- Telegram's servers see which userpics a viewer's WebView loads. Telegram hosts the
  whole session already, so nobody new learns anything.
- Whoever can see a person in Swap sees their photo: their links, people within an
  order's reach (ADR-0028), and the other side of a deal. The privacy page says so
  (K3).
- A userpic URL may change when its owner changes the photo. The next sign-in brings
  the new one.

## Alternatives considered

- **Copying photos through the bot.** That means storage, a job, and care with the Bot
  API file links, which carry the token. The link is enough while Telegram provides it.
- **Initials only** (ADR-0003). The owner asked for photos.
- **Allowing any image host in the CSP.** Telegram's own two are enough.
