# 0032. Deleting all history at once, and the account

Status: Accepted · Date: 2026-10-22 · Spec: §3 «Разрыв связи и удаление», §7 «Приватность»; QUESTIONS K2, Q-B10; builds on ADR-0030

## Context

The owner asked for two buttons in the settings: delete all deal history at once, and
delete the account (K2). Q-B10 already answered how an account goes: refused while a
deal runs; proposals cancelled; links and sessions deleted; the user becomes «Удалённый
участник» within 24 hours. ADR-0030 then defined deleting for oneself and erasing what
everyone has deleted.

## Decision

**«Удалить всю историю»** (`DELETE /me/history`) applies ADR-0030 to everything finished
at once, using the same code as one by one:
- every finished deal the person proposed is deleted for them;
- every order of theirs that isn't open and has nothing running is deleted for them;
- what both sides have deleted is erased.

What still runs stays: running deals, and open orders. The answer counts what was
deleted and what stays, and the profile says so.

**«Удалить аккаунт»** (`DELETE /me`):
- It is refused with 409 `account.deals_running` while any deal of theirs is accepted
  or disputed.
- Their proposals are cancelled quietly, as a broken link's are.
- Their open orders are closed. That cancels the proposals on them and tells those
  proposers, as any closing does (Q-E2).
- Their history is deleted as above.
- Their links, invites, sessions, mutes and messages to them are deleted.
- The row stays, because others may keep deals with it. It is scrubbed: no Telegram id,
  name, @username, photo, language or zone, and `deleted_at` is set. Everything happens
  at once, not within 24 hours.

**Who they are afterwards.** `Person.deleted` is true, and the app names them «Удалённый
участник» in the reader's language. The same Telegram account opening Swap again is a
new user: the old row has no Telegram id to match.

**The app stops asking.** After the account is deleted, the app forgets this launch's
`initData` and shows a closing screen. Signing in again with it would quietly create a
new account.

## Consequences

- Others keep their deals with the person who left, journal and all, until they delete
  them themselves. The score of the others keeps the point.
- **A known gap.** Messages already sent to others, kept in the outbox's table, still
  name the person who left. They go with a retention sweep, which waits in
  «Потенциальные планы».
- The deploy-time dumps, the last five, keep the deleted data until they rotate out. The
  privacy page says so (K3).

## Alternatives considered

- **Deleting the user row.** Deals others keep point at it, and the journal names its
  actors.
- **Waiting 24 hours** (Q-B10's ceiling). Nothing needs the delay, and doing it at once is
  what the person sees happen.
