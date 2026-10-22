# 0033. The agreement at first launch, and a public privacy page

Status: Accepted · Date: 2026-10-22 · Spec: §2 «Юридическая позиция», §7 «Приватность»; QUESTIONS K3, K9, Q-B15

## Context

§2 relies on an agreement saying Swap is not a payment service, takes no part in
settlement and guarantees nothing. Q-B15 planned it for first launch with «Принимаю».
The owner asked for it now, and for a privacy policy URL to set in BotFather (K3). It must
open in a plain browser, where the Mini App would show «Откройте через Telegram». The
owner's address is the contact (K9).

## Decision

**The page** is `frontend/public/privacy.html`: one static page in Russian, English and
Georgian, with links between them, served at `/privacy`.
- The api serves any `<name>.html` of the build at `/<name>`, outside the app's routes,
  so the page needs no script and no session.
- Its own styles are inline, which the CSP allows. It loads nothing else.
- It says what Swap is and isn't, and what is stored. It covers who sees what (reach,
  photos, the network, the score), how long things are kept and how deletion works, the
  deploy-time copies of the database, Sentry, notifications, and the contact.

**The agreement in the app** is three short paragraphs from the dictionaries, a link to
the page, and «Принимаю» in the main button. The app shows it before anything else while
`Me.terms_accepted` is false.
- `users.terms_version` and `terms_accepted_at` record what was accepted and when.
- `TERMS_VERSION` in `swap/api/v1/me.py` is the text's version. A new text bumps it, and
  everyone accepts it again at their next launch. Those already using Swap accept it at
  their next launch.
- **Default:** the text ships as drafted (K3); the owner approves it later, and a change
  comes with a version bump.

**The contact** (K9) is a row in the profile's «О Swap»: format37@gmail.com, copied on a
tap, because `mailto:` may not open inside Telegram. The page has it as a link.

## Consequences

- The privacy URL for BotFather is https://swap.latentstate.dev/privacy.
- The api doesn't refuse requests from someone who hasn't accepted. The app gates them,
  and the bot's greeting says what Swap is, as Q-E3 had it.

## Alternatives considered

- **A route of the Mini App.** Outside Telegram it would show the stub, which is what K3
  rules out.
- **Separate pages per language.** One page with anchors is one URL for BotFather, and it
  reads in any of the three.
