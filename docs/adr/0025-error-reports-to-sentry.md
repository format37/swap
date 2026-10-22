# 0025. Errors go to one Sentry project, with nothing personal in them

Status: Accepted · Date: 2026-10-22 · Spec: §7 «Наблюдаемость», §2 v1; QUESTIONS I1; amends the kickoff's "Sentry is v1"

## Context

The spec puts Sentry in v1 and asks for personal data to be cut out of it. On
2026-10-22, during phase 1, the owner asked for it now (I1). He wants one new project for
Swap, separate from Phonyx's, and only production exists.

Three things would leak without care:
- **The bot token.** It is in every Bot API URL, so in breadcrumbs, exception messages
  and log lines. `swap.logs.Redactor` already cleans our logs of it (ADR-0011).
- **initData.** It is a sign-in's request body. Telegram also puts it in the Mini App's
  URL hash, and the `MemoryRouter` never changes the URL.
- **People's data.** Relay requests carry their messages, and SQL parameters carry
  amounts and names.

## Decision

**One project, `swap`, in `personal-htg`.** The api, the worker and the Mini App all report
to it. A `service` tag (`api`, `worker`) and the platform tell them apart. The
environment is `APP_ENV`, so production's reports say `prod`.

**One setting, `SENTRY_DSN`, in `.env`.**
- The api and the worker read it at run time; unset, `init_sentry` does nothing.
- The image build passes it to Vite as `VITE_SENTRY_DSN`. A build without it ships a
  bundle that sends nothing.
- The CSP's `connect-src` names the DSN's host, and only when there is one.
- The release is the commit: `vps.sh` passes `SENTRY_RELEASE` to the build.

**What is sent:** errors, plus 10 % of traces. Health checks are never traced.

**What is not sent:**
- **Backend:** no user info, cookies, query strings, request bodies, SQL parameters or
  local variables. Every event, transaction and breadcrumb goes through `Redactor`
  last.
- **Log records:** errors logged through structlog become reports titled by the log's
  event, with redacted fields. `configure_logging` now puts the exception on the stdlib
  record, where Sentry looks for it.
- **Mini App:** no user info, cookies, bodies or query strings. Every event, span and
  breadcrumb loses the URL's hash before it leaves.
- **No session replay:** it records people's screens, and it would add 50 KB to the
  bundle.

## Consequences

- An error in production reaches Sentry with its stack and its commit, and no person in
  it.
- **Minified frontend frames.** The Mini App's stack frames point into the minified
  bundle. Readable ones need source maps uploaded at build time with an auth token on
  the VPS, which is a later PR if the frames get in the way.
- **IP addresses.** Sentry still infers a location from the sender's address. Turn on
  "Prevent Storing of IP Addresses" in the project's Security & Privacy settings; the
  SDKs can't do that.
- **Bundle size.** It grows by about 30 KB gzip, and stays far under the 300 KB budget.

## Alternatives considered

- **Two projects, backend and frontend, like Phonyx.** It's cleaner to filter, but it
  means two DSNs to manage, and the owner asked for one project.
- **A tunnel through the api instead of a CSP entry.** It survives ad blockers, but
  inside Telegram there are none, and it adds an endpoint.
- **Sentry's recommended `send_default_pii` and replay.** They break the spec's rule to
  strip personal data.
