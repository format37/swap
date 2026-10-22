# 0029. A person's score: how many different people they settled a deal with

Status: Accepted · Date: 2026-10-22 · Spec: §2; QUESTIONS J5; overrides §2's «репутация, видимая за пределами личных связей»

## Context

§2 keeps reputation out of Swap, and so did CLAUDE.md. The owner asked for a count of
successful deals, called a score, with at most one point per counterpart, so that two
people can't pump each other's score (J5). With reach (ADR-0028), people see orders
from beyond their own links, and the score tells them something about the author.

## Decision

**The score** is the number of different people someone has a settled deal with.
Repeat deals with the same person add nothing.

**It is counted, not stored.** `User.score` is a `column_property`: a correlated count of
distinct counterparts in settled deals, which the database works out whenever it loads a
user. Every person a response shows carries it, and no endpoint asks for it on its own.
- It survives a flush of the user's own columns (`expire_on_flush=False`). Reading it
  again there would be a query where async allows none.
- The sign-in's upsert loads it explicitly: `INSERT … RETURNING` brings columns only.
- Deal responses read their people afresh, because a deal that just settled changed
  both scores.

A deal that both sides deleted is erased (ADR-0030), and its point goes with it. Keeping
points apart from deals would keep who dealt with whom after both had asked to erase
it.

**Where it shows.** The api's `Person` and `Me` gain `score`. The `Person` component
(ADR-0027) shows it beside the name, with a handshake icon, wherever a person is shown.
On a card's heading, the profile and a link's screen, a tap opens Telegram's popup:
«Успешные сделки с разными людьми: 7. Повторные сделки с тем же человеком не
прибавляют.» In rows that are buttons themselves it only shows. A score of 0 is shown
too: a newcomer is a newcomer.

**Policy.** This is the one standing a person has in Swap. There are no ratings, no
reviews, and nothing anyone writes about anyone else.

## Consequences

- **A known limit.** Someone with several Telegram accounts can settle deals among
  them. In a network that grows only by invitation, the owner accepts that.
- The count runs per response. It reads the deals of the people shown, which at Swap's
  scale is a few rows.

## Alternatives considered

- **A stored counter,** updated when a deal settles. It would need care when deals are
  erased, and it saves a query that costs nothing.
- **Counting deals, not people.** Two friends could then pump each other's score, which
  is what the owner ruled out.
- **Counting every finished deal.** A cancelled deal says nothing about trust.
