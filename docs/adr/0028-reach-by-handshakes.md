# 0028. An order reaches as far along chains of links as its author says

Status: Accepted · Date: 2026-10-22 · Spec: §2, §3, §5, FR-2.1, FR-2.4, FR-7.1; QUESTIONS J2; amends ADR-0016 and ADR-0023; overrides §3 «Связь не транзитивна» and §5 «Создаётся только между сторонами с активной связью»

## Context

Until now an order was visible only along a single active link (§3, ADR-0016). Links were
not transitive, and nobody saw anyone else's links. The wizard offered «Всем моим
связям» or «Только выбранным».

The owner replaced that with a reach in handshakes, set per order from 0 to ∞, and a
filter for whoever looks at the feed (J2). There are no circles and no groups. The owner
asked whether this complicates people's lives. The answer given: not if the slider speaks
in words and its defaults can't break.

## Decision

**Distance** is the number of handshakes over active links between two people. Your
links are 1, their links are 2, and so on. Two people with no chain of active links
between them have no distance at all. A broken link can split the network into islands
that never see each other.

**Reach** is `orders.reach`, a small integer from 0 to 3, or NULL for ∞:
- 0 is «Только выбранным»: the order's list in `order_visibility`, picked from the
  author's own links;
- 1 is «Мои связи»;
- 2 is «мои связи и их связи», the default for new orders;
- 3 is one handshake further;
- ∞ is «Вся сеть»: everyone with any chain to the author.

The list exists only at 0. Migration 0016 keeps every existing order as it was: reach 1
for those without a list, 0 for those with one.

**Who sees an order.** `open_to(viewer, within)` stays the one predicate (ADR-0016). The
author always sees their order. Anyone else sees it when all of these hold:
- it isn't deleted, it is open, and its last day hasn't passed;
- at reach 0: the viewer is on its list and still linked to the author;
- at reach 1, 2 or 3: the viewer is at most that many handshakes away;
- at ∞: some chain exists;
- the viewer's own filter, `within`, isn't narrower.

`seen_by` adds the history, as before (ADR-0023). An order that isn't open to someone
answers 404, as one that doesn't exist.

**How distance is computed.** A recursive CTE walks active links out from the viewer and
caps the depth at 4, meaning "four or more". Reach and the filter tell only 1, 2, 3 and ∞
apart, so 4 is enough. Postgres's `UNION` drops rows it has already produced, and with
the cap there are at most four rows per person. The walk ends however the links loop,
and it touches each link a few times at most. At Swap's scale that is microseconds, and
it needs no table to keep in step with the links.

**The viewer's filter.** «Открытые мне» takes `within` = 1, 2 or 3, or nothing for ∞,
the default. On Home it is folded under one line that says «Вся сеть» until someone
opens it. Its 0, favourites, waits in «Потенциальные планы».

**Proposals across handshakes.**
- Anyone who sees an order may propose on it, without a direct link first: the author
  chose the reach.
- The card shows how the viewer reaches the author, through one shortest chain of names
  («через Нино → Гиорги»). It also shows the author's score (ADR-0029).
- A deal outlives a broken chain. Once proposed, it stays visible to both sides.
- A broken direct link between the two still cancels their unanswered proposals (Q-B9).
  A break farther along the chain cancels nothing.

**Telling people.** The bot announces a new order to direct links only, or to the list
at 0. Farther rings find it in the feed.

**The wizard.** Step 2's slider has five stops: «Только выбранным», «Мои связи», «2
рукопожатия», «3 рукопожатия» and «Вся сеть». Under it stands who will see the order,
«4 ваших связи и ещё 11 человек», and the picture:
- rings around the author, one per handshake, with avatars and names (ADR-0027);
- plain SVG, with no library;
- beyond the third ring, a count instead of faces. Names that far away don't help the
  author decide, and the count is all the line under the slider needs.

At 0 the picture gives way to the author's links to choose from. «Только выбранным»
needs at least one person, so the slider has no broken state.

**`GET /api/v1/network`** returns the signed-in user's rings: who is 1, 2 and 3
handshakes away, and how many are farther. It names people beyond one's own links,
which §3 forbade («никто не видит чужих связей»). The owner's picture needs it.

**Policy.** This overrides §3 and the old CLAUDE.md rule, now rewritten: visibility
follows chains of active links, up to the author's reach. What stays:
- no escrow;
- no money moved;
- nothing visible to anyone with no chain of links to the author.

## Consequences

- At the default of 2, a newcomer's name, photo and amount reach their links and their
  links' links. Nobody five acquaintances away sees them until the newcomer moves the
  slider.
- The negative tests come first:
  - a viewer one ring too far;
  - a broken link in the middle of a chain;
  - an order at 0 and someone not on its list;
  - the filter.
- The texts that promised «знакомые ваших знакомых вас не видят» change, in the app and
  in the bot.

## Alternatives considered

- **Circles or groups of friends.** The owner sees no reason for them: a person, their
  links, and the reach they set.
- **A web of lines.** On a phone it stops being readable at about fifteen people. Rings
  stay readable, and every ring's meaning is the slider's.
- **A table of distances, kept in step with every link change.** It would be faster at
  a scale Swap won't reach, and it would be one more thing to get wrong.
- **Walking the graph in Python.** It is simple too, but the feeds filter orders in SQL.
  One predicate in SQL keeps visibility in one place.
