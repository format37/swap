# 0001. `swap.latentstate.dev` at the root of its own origin, one upstream, behind the shared Caddy

Status: Proposed · Date: 2026-10-21 · Spec: §9 «Домен», §13 row 1

## Context

The spec recommends the subdomain and allows `latentstate.dev/swap` if there is a
technical reason. The VPS already runs one Caddy 2.8 (`reverse-proxy`, in
`~/reverse-proxy/`) that owns :80/:443 for every site on the box, issues its own
certificates for `latentstate.dev` hostnames (grey-cloud A records), and reaches app
containers by name over the external `mcp-shared` network. The other sites there
send `X-Frame-Options: DENY`; Telegram Web renders a Mini App inside an iframe on
`web.telegram.org`.

## Decision

1. Swap is served from the root of `https://swap.latentstate.dev`. There is no path
   prefix anywhere: Vite `base: '/'`, no router basename, no FastAPI `root_path`.
2. There is one upstream. The frontend is built into the api image (spec §9) and the
   api serves it, so Caddy proxies everything to `swap-api:8000`:

   | Path | Served by |
   |---|---|
   | `/api/v1/*` | REST |
   | `/tg/webhook` | aiogram, behind `X-Telegram-Bot-Api-Secret-Token` |
   | `/healthz` | api liveness, database, worker heartbeat age |
   | `/assets/*` | hashed build output, `Cache-Control: public, max-age=31536000, immutable` |
   | anything else | `index.html` with `no-cache`; the client router takes over |

3. Production gets a site block, kept in the repo as `deploy/Caddyfile-swap.caddy`
   (the phonyx pattern) and appended to the shared Caddyfile. There is no Swap-owned
   Caddy on the VPS. The local stack runs its own `caddy:2.8` with the same routes, so
   dev matches prod.
4. The block sets HSTS, `nosniff`, `Referrer-Policy: no-referrer`, and a CSP with
   `default-src 'self'` and `frame-ancestors https://web.telegram.org`. It sends no
   `X-Frame-Options`, which would show a blank page in Telegram Web. It also sets
   `lb_try_duration`, so requests wait out an api restart instead of getting a 502,
   and a `handle_errors` response («Swap обновляется, попробуйте через минуту») for
   when the api stays down. That line is the one user-facing string outside the
   dictionaries, because the shared Caddy can't read them. The exception is
   deliberate.

## Consequences

- Isolation. A separate origin shares no storage, cookies or same-origin script access
  with the other apps on `latentstate.dev`. Under `/swap`, an XSS in any sibling app
  would be an XSS in Swap.
- The webhook URL is `https://swap.latentstate.dev/tg/webhook`, and the Mini App URL
  is the origin root.
- The owner has to act twice: create one grey-cloud A record, and approve an
  inode-preserving edit of `~/reverse-proxy/Caddyfile` plus `caddy reload`. Neither
  happens without a go in the current session (kickoff hard rules).
- A staging copy, if wanted, is another block (`swap-next.latentstate.dev`) in front
  of a second compose project, like `~/phonyx-staging`.

## Alternatives considered

- **Path `latentstate.dev/swap`.** It needs `base` in Vite, a router basename, a
  prefixed API, and the `handle` vs `handle_path` choice (the double-strip trap in the
  VPS runbook). It also shares an origin with every other app. No technical reason
  favours it.
- **A Swap-owned Caddy in production** (the spec's "four containers"). It cannot bind
  :443 next to `reverse-proxy`, and chaining it behind the shared one adds a hop and a
  second TLS configuration for nothing.
- **A separate nginx `web` container** (phonyx). It keeps the page shell loading
  while the api is down, but a Mini App can do nothing without the api. The
  `handle_errors` page covers the "down" message without a fifth container.
