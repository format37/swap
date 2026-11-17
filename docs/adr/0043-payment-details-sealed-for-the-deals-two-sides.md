# 0043. Payment details again: the payee's own words, sealed, seen by the deal's two sides

Status: Accepted · Date: 2026-11-17 · Spec: §5 DealLeg, FR-4.1; QUESTIONS Q1; amends ADR-0021, brings back ADR-0004's sealing; the kickoff's rule on recipient details

## Context

ADR-0021 took payment details out (G3). The form that required them had stopped every
proposal at the demo, and the parties settled where to pay in Telegram.

After the first real deals, the owner asked for the opposite, with nothing required: a
text on each transfer's card, beside «Деньги отправлены» and «Деньги получены», for a
card or account number. He also asked for one on each currency an order takes (Q1).

The kickoff still holds for such text: recipient details are encrypted in the app before
they reach the database, and are masked in every log line and api response except to
those the leg is for.

## Decision

**Two optional fields, never required:**
- `order_wants.details`: where the order's author takes that currency.
- `deal_legs.details`: where the leg's payee takes that transfer.

Each holds at most 500 characters of the person's own words, such as «TBC 4276 …,
Alex».

**Sealed** with AES-256-GCM, by `swap/crypto.py`, back from commit `c227910^`. The keys
come from `RECIPIENT_KEYS` in `.env`, never from the database. The associated data names
whose details they are: the author for an order's, the payee for a leg's.
- So the author's details move to their own leg as they are.
- Copied into someone else's row, they won't open.
- The envelope keeps a mask, «•••• 9012», in the clear.

**Who writes:**
- The order's author, per wanted currency, in the wizard. A monthly copy keeps them.
- A leg's payee, on the deal's card, while the deal is proposed or accepted, and until
  the payer marks the leg sent. `PUT /deals/{id}/legs/{seq}/details`; blank clears it.
- No journal line: changing them moves nothing.

**Who reads:**
- An order's details: its author alone. The api says `null` to anyone else who sees
  the order.
- A leg's details: the deal's two sides, the only ones who ever see a deal.
- Accepting a deal copies the author's details for its currency onto the leg that pays
  them, unless that leg has some already.

**Nowhere else:** not in bot messages, CSV exports, logs or error reports. Sentry keeps no
request bodies, SQL parameters or local variables (ADR-0025), and the log redactor knows
the keys.

**Without a key** a server refuses to save details (503 `details.off`) and shows none.

**Deleting an account** clears the person's details everywhere, on legs others keep too.

**The agreement goes to version 2.**
- Its data line and the privacy page say what is stored, sealed, and who sees it.
- Everyone accepts the new text once, at their next launch.

## Consequences

- A dump or a backup without the key holds no card numbers, only their last four
  digits.
- Losing the key loses every saved detail. The owner keeps a copy off the server.
- A payer reads the payee's card on the leg and copies it in one tap. Nobody types it
  into a Telegram chat any more.
- A proposer gives their own details on the deal's card, or in the proposal's comment
  as before.

## Alternatives considered

- **Plain text.** Simpler, but the kickoff's rule is explicit, and the sealing code
  already existed.
- **An order's details for everyone who sees the order.** That spreads a card number
  along every chain of links the reach allows.
- **Copying them at the proposal.** Anyone within reach could read them by proposing and
  withdrawing.
- **Either side writes either leg.** It blurs who said where to pay. The payee owns that
  word, and once money is sent, it stays as it was.
- **Saved details per person, as ADR-0010 had.** That brings back the step G3 removed.
