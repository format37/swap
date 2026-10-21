# 0004. `rate_spec` and `recipient_details`: versioned JSONB, the second one encrypted

Status: Proposed · Date: 2026-10-21 · Spec: §5, FR-3.1–3.5, §7 «Безопасность», §13 row 4

## Context

§13 sets both fields as JSONB, with recipient details only ever encrypted. An order
can want several currencies (`wants[]`), so a single `base/quote` pair can't describe
a fixed rate. Money is never a `float` (§7), so a JSON number is a trap: JavaScript
and Python's `json` both parse it as one.

## Decision: `orders.rate_spec`

The field is a discriminated union, validated by Pydantic (`extra="forbid"`), with a
shape version `v` and decimals as strings:

```json
{"v": 1, "type": "fixed",
 "quotes": [{"base": "GEL", "quote": "RUB", "value": "29.20"},
            {"base": "USD", "quote": "RUB", "value": "81.50"}]}

{"v": 1, "type": "reference", "source": "manual", "label": "NBG", "markup_pct": "-1.0"}

{"v": 1, "type": "reference", "source": "nbg", "markup_pct": "-1.0", "lock_at": "accept"}
```

- A fixed rate has one quote per wanted currency, each saying "1 base = value quote".
  It is stored in the direction the author typed it («1 GEL = 29,20 RUB»), so it
  displays the way they think. `base`/`quote` must be the give currency and that
  wanted currency, in either order.
- `markup_pct` lies in [−5.0, +5.0] in steps of 0.1 (FR-3.2). `lock_at` (propose /
  accept / send, default accept) applies only to live sources, which arrive in v1.
  What `manual` means in the MVP is question Q-B3 in `QUESTIONS.md`.
- The database CHECKs `rate_spec->>'type' IN ('fixed', 'reference')`. Anything deeper
  is the model's job. A new shape bumps `v` and comes with a data migration.

**The formula has one implementation** (`swap/domain/rates.py`), and the UI never
does money arithmetic:

```
r            = rate(give → want)        # value, or 1/value when the quote is stated the other way
amount_want  = round_half_up(amount_give × r × (1 + markup_pct / 100), 2)
```

The calculation runs in a 28-digit `Decimal` context and rounds once, at the end.
Live previews in the wizard and in the proposal come from an api endpoint, debounced
in the UI. A deal stores its own copy of `rate_spec`, `rate_value`, `rate_locked_at`
and `rate_quote_id` (source and time). Its leg amounts are the source of truth.
Nothing is recalculated afterwards (FR-3.5).

## Decision: `deal_legs.recipient_details`

- The plaintext is a small typed object, `{"kind": "card", "card_number": "…",
  "holder": "…", "bank": "…"}`, with the fields varying by kind (card, SBP, bank,
  cash, other). In memory it is held as Pydantic `SecretStr`, so a stray `repr` or log
  call prints stars.
- It is encrypted in the app with AES-256-GCM (`cryptography`'s `AESGCM`), using a
  random 96-bit nonce. The associated data is
  `swap/deal_leg/<leg_id>/recipient_details/v1`, which binds the ciphertext to its row:
  copied into another leg, it fails to decrypt.
- It is stored as a JSONB envelope: `{"v": 1, "kid": "k1", "nonce": "…", "ct": "…",
  "mask": "•••• 5678"}`. The mask is made at write time from the plaintext (last four
  digits of a card, last two of a phone, «•••» for free text), so the api can show it
  without decrypting.
- Keys come from the environment (`RECIPIENT_KEYS=k1:<base64url>,…`,
  `RECIPIENT_KEY_ID=k1`), never from the database. To rotate, add a key id, make it
  active, and let a worker job re-encrypt the old rows.
- The api returns `{"masked": …, "full": null}` to anyone who isn't allowed to see
  the full value; Q-B8 says who is. Logs go through a structlog processor that
  replaces a denylist of keys (`recipient_details`, `card_number`, `phone`, `holder`,
  `init_data`, `token`), and request and response bodies are never logged.
- A worker job sets `recipient_details` to NULL 30 days after the deal closes (§5).

## Consequences

- A stolen database dump or backup holds ciphertext only, because the key isn't in
  it. The flip side: if the key is lost, so are the details. That is acceptable for
  data that lives at most 30 days past a deal. The owner keeps a copy of the key
  outside the server.
- Decimals pass through JSON as strings end to end. The UI formats them with
  `Intl.NumberFormat`, which accepts decimal strings without a float round trip.
- Fixed rates for two wanted currencies are two numbers the author types. The wizard
  asks for each.

## Alternatives considered

- **`pgcrypto`.** The key would travel to Postgres inside SQL text, where statement
  logs and `pg_stat_statements` can catch it. Encrypting in the app keeps the key out
  of the database process entirely.
- **A `bytea` column.** It works, but the envelope's key id and mask would need
  columns of their own, and §13 says JSONB.
- **Rate columns instead of JSON.** Three rate types with different fields would
  mean nullable columns and CHECKs per type. Pydantic validates the union in one
  place.
