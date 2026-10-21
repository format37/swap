# Swap

Swap is a Telegram Mini App for people who know each other and need money in another
country. One of them has roubles in Russia and wants lari in Georgia; the other has it
the other way round. Instead of an exchange, they swap: each pays the other's
recipient at home.

In Swap they announce what they have, agree on a deal, and walk it through a strict
sequence: who sends first, «Отправил», «Получил», then the second leg. Both sides
always see who owes whom.

**Swap never holds, moves or guarantees money.** It is a planner and a journal, not an
exchange. There is no public order book, no search among strangers and no escrow. You
see only the people you have linked with by personal invitation, and links are not
transitive.

Status: phase 1, the MVP, is being built. The bot is
[@peertopeerswapbot](https://t.me/peertopeerswapbot).

## Stack

- Python 3.12, FastAPI, aiogram 3, SQLAlchemy 2 (async), Alembic, PostgreSQL 16.
- APScheduler in a separate worker.
- React 18, TypeScript, Vite, Tailwind, TanStack Query and `@tma.js/sdk-react`.
- Docker Compose, behind Caddy.
- Interface in Russian, English and Georgian.

## Docs

- [`docs/tech-specs.md`](docs/tech-specs.md): the specification (in Russian).
- [`docs/adr/`](docs/adr/): one page per decision.
- [`docs/QUESTIONS.md`](docs/QUESTIONS.md): open questions and the owner's answers.
- [`docs/plan.md`](docs/plan.md): the phases, the current checklist and the estimates.
- [`CLAUDE.md`](CLAUDE.md): working rules for whoever changes the code, human or not.

## Licence

[MIT](LICENSE).
