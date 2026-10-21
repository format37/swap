# 0003. Own UI primitives on Tailwind, Telegram-native controls, no component library

Status: Proposed · Date: 2026-10-21 · Spec: §8, §11, §13 row 3

## Context

The bundle must stay under 300 KB gzip, with cold open in under 2 s on 4G (§7).
Colours come only from Telegram's `themeParams`, with no backgrounds of our own and
no custom design system before v1 (§11). The screens in §11 are lists, cards, a
three-step form and a proposal form. Every irreversible action is confirmed through
the native `showConfirm`, and each screen's main action sits in Telegram's
`MainButton`.

## Decision

- No component library. About fifteen primitives live in `frontend/src/ui/`: Button,
  Cell (list row), Section, Card, StatusLine, AmountInput, Field, Segmented, TabBar,
  Sheet, EmptyState, Skeleton, Avatar (initials, no photos), Badge and Toast. They are
  plain React and Tailwind v4.
- Every colour is a Telegram theme variable. Tailwind's `@theme` maps
  `bg`/`text`/`hint`/`link`/`button`/`secondary-bg`/`destructive` to
  `var(--tg-theme-…)`, so a component can't name a colour of its own and dark mode
  comes for free.
- Native form controls wherever the platform does better: `<select>`, `<input
  type="date">`, `<input type="range">` for the amount slider, and
  `inputmode="decimal"` for the numeric keypad. Native date and select pickers on iOS
  and Android beat anything we could ship.
- Telegram draws the heavy chrome itself: `MainButton`, `SecondaryButton` and
  `BackButton`, `showConfirm` / `showPopup`, and `HapticFeedback`. Those cost us no
  bytes.
- Budget. The libraries the spec already names (React 18 with React DOM, TanStack
  Query, react-hook-form, zod, the Telegram SDK per Q-A8, and the API client) come to
  roughly
  100–130 KB gzip. That leaves well over half the budget for our code and a router.
  CI measures the gzip size of the initial JS and CSS and fails the build above
  300 KB, so the limit is a test rather than a hope.
- If a widget turns out hard to make accessible (most likely a bottom sheet),
  importing that one Radix primitive is allowed, with a short ADR.

## Consequences

- We own the accessibility of a few custom widgets (TabBar, Segmented, Sheet).
  Testing Library tests query them by role, which keeps that honest.
- The look follows the user's Telegram theme on iOS, Android and Desktop, with no
  second theme to keep in sync.
- The style matches the owner's other frontends: no semicolons, single quotes,
  PascalCase function components, and every colour a `var(--token)`.

## Alternatives considered

- **shadcn/ui.** Radix plus copied-in components. It has good accessibility, but it
  brings its own token system, which we would rewrite to `themeParams` anyway, and a
  Radix runtime per widget.
- **Telegram UI** (`@telegram-apps/telegram-ui`). The look is closest to native
  Telegram, but it ships its own CSS system next to Tailwind and costs more of the
  budget than the screens need.
- **Headless UI or Konsta UI.** We would use one or two Headless UI components, and
  Konsta imitates iOS or Material rather than Telegram.
