# 0010. Payment details: saved free text per asset, copied into the deal

Status: Accepted · Date: 2026-10-21 · Spec: §5 `recipient_details`, §13; the owner, 2026-10-21

## Context

Once two people agree on a deal, each payee has to tell the payer where to send the
money: an account, a card, a phone number for a bank transfer, or a wallet. The spec
has the acceptor type recipient details into each deal and leaves saved recipients
for v2. The owner, on 2026-10-21: the details can be predefined free text for each
asset, bank or institution, they can be crypto, and the format is mine to choose.

## Decision

- **Each user keeps a list of payment details.** An entry has:
  - an **asset**: RUB, GEL, USD, EUR, USDT, USDC, … (ADR-0002);
  - a **kind**, each with its own icon: bank account, card, phone transfer, crypto
    wallet, cash, other;
  - a short **title**, stored in the clear: «TBC», «Сбер · СБП», «USDT · TRC20»;
  - free **text**, up to 500 characters, holding whatever the payer needs: IBAN or
    card number, holder, bank, network and address, memo.
- **Free text, not fields.** Formats differ by country, bank and chain: IBAN, card,
  an SBP phone number, a Georgian account, a TRC20 address with a memo. The payer
  pastes them into their own bank or wallet app anyway, so the card has a
  «Скопировать» button.
- **At the deal.** The proposer picks one of their entries for the asset they receive
  when proposing. The acceptor picks theirs when accepting, or adds one on the spot.
  Cash needs no details, only an optional note on where to meet. The chosen entry is
  **copied** into the leg (`deal_legs.recipient_details`), so editing or deleting the
  saved entry later changes no deal in progress.
- **Encryption** (ADR-0004). The saved text and the leg's copy are both AES-GCM
  envelopes, each bound to its own row through its associated data. The kind and the
  title stay in the clear for lists and bot messages; the text is ciphertext plus a
  mask.
- **Who sees it** (Q-B8). The payer sees the leg's details in full once the deal is
  accepted, and the payee always sees their own. Everyone else, every log line and
  every bot message get the mask.
- **Crypto.** USDT and USDC only in the MVP. They are dollars at two decimals, so
  `numeric(18,2)` still holds. BTC, ETH or TON would need more decimals per asset,
  which is a schema decision for later. For crypto the UI shows «Проверьте сеть»
  beside the details.
- **Retention.** A leg's copy is purged 30 days after the deal closes (§5). Saved
  entries live until their owner deletes them or deletes the account.

## Consequences

- Nothing validates account numbers. People catch typos: the payee sees their own text
  in full, and the payer sees it before sending.
- Swap now keeps bank details for as long as a user wants, not 30 days at most. That
  raises the stakes of the key, so the owner keeps an off-box copy (ADR-0004).
- The MVP profile gains a «Реквизиты» section, and Q-B16's "no saved recipients" no
  longer holds.

## Alternatives considered

- **Structured, per-country fields** with IBAN and Luhn checks. Weeks of work for
  formats we can't enumerate, and they would still need an "other".
- **Typing details into every deal** (the spec's MVP). The owner asked for predefined
  entries, and retyping a card number is where typos come from.
- **Sending details as a chat message between the two.** Not encrypted by us, not tied
  to a deal, and lost in the chat history.
