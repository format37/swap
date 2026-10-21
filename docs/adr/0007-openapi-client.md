# 0007. The TypeScript client is generated from FastAPI's OpenAPI: openapi-typescript + openapi-fetch + openapi-react-query

Status: Proposed · Date: 2026-10-21 · Spec: §8 «Состояние и данные», §10, §13 row 7

## Context

Frontend types are never written by hand (§13). FastAPI derives OpenAPI from the
Pydantic models (§8). TanStack Query is the cache, the bundle budget is 300 KB gzip,
and money crosses JSON as a string (ADR-0004).

## Decision

- **`openapi-typescript`** (7.x) turns the schema into `frontend/src/api/schema.d.ts`.
  That file is types only, with zero runtime.
- **`openapi-fetch`** (0.17) is the HTTP client, typed by those paths. It is a few
  KB, and one middleware on it:
  - adds the `Authorization` header (Q-A4);
  - turns `application/problem+json` into a typed `ApiError` carrying the machine
    `code` (`deal.invalid_transition`, …), which the UI maps to a dictionary string.
- **`openapi-react-query`** (0.5.x, pinned: the 1.0.0 on npm is a deprecated bad
  publish) binds the client to TanStack Query:
  `$api.useQuery('get', '/api/v1/deals/{deal_id}', { params: { path: { deal_id } } })`.
  Query keys derive from path and params, so invalidating after a mutation is
  predictable.
- **The schema is exported without a running server**
  (`uv run python -m swap.tools.openapi > frontend/openapi.json`), and
  `npm run gen:api` regenerates `schema.d.ts`. Both files are committed, so a PR's
  diff shows its contract change. CI regenerates both and fails on any difference.
- **On the FastAPI side,** `generate_unique_id_function` gives readable operation ids.
  Input and output schemas stay separate (FastAPI's default), so a `Decimal` in a
  response is `string` in TypeScript. For requests, FastAPI would emit
  `number | string` for a `Decimal`. Money fields in request models therefore use an
  annotated `Decimal` whose JSON schema is string-only, so the generated request type
  doesn't accept a JS number.
- **zod schemas describe what a person types into a form**: strings from inputs, the
  wizard's steps. At submit they are mapped into the generated request types. The API
  types themselves are never written by hand.

## Consequences

- A backend change that breaks the frontend fails `tsc` in the same PR.
- The generated code is one declaration file, with nothing to review line by line and
  nothing added to the bundle.
- Amounts stay strings end to end. There is no number parsing anywhere in the client.
- **Maintenance risk.** `openapi-fetch` and `openapi-react-query` are still 0.x, and
  their shared repository has seen only dependency bumps since March 2026; in July a
  maintainer said it is maintained but that he is "swamped". Both are small (a vendored
  copy would be a few hundred lines, MIT). The contract is `openapi.json`, not these
  libraries, so if they stall, the fallback is Orval generating from the same file.
  That swap touches only `frontend/src/api/`.

## Alternatives considered

- **Orval** (8.x, very active). The strongest alternative and the fallback above. It
  generates a hook per operation, plus zod, which is a lot of generated code to keep
  in step with TanStack Query versions, and it needs more configuration.
- **`@hey-api/openapi-ts`.** Capable, but a larger generated SDK where we only need
  types and a thin client.
- **`openapi-generator` (typescript-fetch).** It needs a Java toolchain in CI and
  generates verbose classes.
- **Hand-written fetch wrappers.** Ruled out by §13.
