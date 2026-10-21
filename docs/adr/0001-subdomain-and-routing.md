# 0001. `swap.latentstate.dev` at the root of its own origin, one upstream, behind the shared Caddy

Status: Accepted (amended on acceptance) · Date: 2026-10-21 · Spec: §9 «Домен», §13 row 1

## Context

The spec recommends the subdomain and allows `latentstate.dev/swap` if there is a
technical reason. The VPS already runs one Caddy 2.8 (`reverse-proxy`, in
`~/reverse-proxy/`) that owns :80/:443 for every site on the box, issues its own
certificates for `latentstate.dev` hostnames (grey-cloud A records), and reaches app
containers by name over the external `mcp-shared` network. Its Caddyfile is a single
hand-edited file shared by many sites, and the owner's condition for touching it is
that nothing else breaks (Q-A3). The other sites send `X-Frame-Options: DENY`, but
Telegram Web renders a Mini App inside an iframe on `web.telegram.org`.

## Decision

1. Swap is served from the root of `https://swap.latentstate.dev`. There is no path
   prefix anywhere: Vite `base: '/'`, no router basename, no FastAPI `root_path`.
2. There is one upstream. The frontend is built into the api image (spec §9) and the
   api serves it, so Caddy proxies everything to `swap-api:8000`:

   | Path | Served by |
   |---|---|
   | `/api/v1/*` | REST |
   | `/healthz` | liveness, database, worker heartbeat age |
   | `/assets/*` | hashed build output, `Cache-Control: public, max-age=31536000, immutable` |
   | anything else | `index.html` with `no-cache`; the client router takes over |

   Telegram never calls this origin. Updates reach the worker through the relay on the
   host's loopback (ADR-0008), so there is no public webhook path.
3. The api sets every security header itself, in one tested middleware: HSTS,
   `nosniff`, `Referrer-Policy: no-referrer`, and a CSP with `default-src 'self'` and
   `frame-ancestors https://web.telegram.org`. It sends no `X-Frame-Options`, which
   would show a blank page in Telegram Web. A header change therefore ships with a
   deploy and never needs an edit of the shared Caddyfile.
4. The production site block lives in the repo as `deploy/Caddyfile-swap.caddy` (the
   phonyx pattern) and is appended to the shared Caddyfile once. It only proxies:
   - compression;
   - `lb_try_duration` with `request_buffers`, so a request waits out an api restart
     instead of getting a 502;
   - a `handle_errors` page for when the api stays down. Its one line, in all three
     languages (ADR-0009), is the only user-facing text outside the dictionaries,
     because the shared Caddy can't read them.
5. The local stack runs its own `caddy:2.8` with the same block minus TLS, so dev
   matches prod.

## Consequences

- Isolation. A separate origin shares no storage, cookies or same-origin script access
  with the other apps on `latentstate.dev`. Under `/swap`, an XSS in any sibling app
  would be an XSS in Swap.
- The Mini App URL is the origin root, and that is what BotFather's Main Mini App
  points at.
- The owner acts once: one grey-cloud A record. The Caddyfile is edited once, in an
  inode-preserving way (`cat >>`), with a dated backup beside it. It is validated with
  `caddy validate` before `caddy reload`, and every other site is probed before and
  after.
- A staging copy, if one is ever wanted, is another block (`swap-next.latentstate.dev`)
  in front of a second compose project, like `~/phonyx-staging`.

## Alternatives considered

- **Path `latentstate.dev/swap`.** It needs `base` in Vite, a router basename, a
  prefixed API, and the `handle` vs `handle_path` choice (the double-strip trap in the
  VPS runbook). It also shares an origin with every other app. No technical reason
  favours it.
- **A Swap-owned Caddy in production** (the spec's "four containers"). It can't bind
  :443 next to `reverse-proxy`, and chaining it behind the shared one adds a hop and a
  second TLS configuration for nothing.
- **Security headers in the Caddy block** (this ADR's first draft). Every CSP change
  would be another hand edit of a file that many sites share.
- **A separate nginx `web` container** (phonyx). It keeps the page shell loading while
  the api is down, but a Mini App can do nothing without the api. The `handle_errors`
  page covers the "down" message without a fifth container.
