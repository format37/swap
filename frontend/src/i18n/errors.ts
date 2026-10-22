import { ApiError } from '../api/client'
import type { MessageKey } from './ru'

// The api's machine codes that have words of their own (ADR-0007).
const BY_CODE: Partial<Record<string, MessageKey>> = {
  init_data_expired: 'error.reopen',
  network: 'error.network',
  'link.not_found': 'error.link_not_found',
  'link.invalid_state': 'error.link_changed',
  'invite.limit': 'error.invite_limit',
  'user.not_found': 'error.user_not_found',
  'link.self': 'error.link_self',
  'link.cooldown': 'error.link_cooldown',
  'order.not_found': 'error.order_not_found',
  'order.not_open': 'error.order_not_open',
  'order.insufficient_remaining': 'error.order_short',
  'order.window_past': 'error.order_window_past',
  // Someone changed it in another window: closed, reopened or deleted it.
  'order.not_closed': 'error.order_changed',
  'order.open': 'error.order_changed',
  'deal.not_found': 'error.deal_not_found',
  'deal.invalid_transition': 'error.deal_changed',
  'deal.not_your_move': 'error.deal_not_yours',
  'deal.expired': 'error.deal_expired',
  'deal.running': 'error.deal_running',
  'deal.delete_with_order': 'error.deal_changed',
  'order.deals_running': 'error.order_deals_running',
}

// Whatever else an order's or a deal's refusal says, its form checked before sending.
const BY_PREFIX: [RegExp, MessageKey][] = [
  [/^(order|rate)\./, 'error.order_invalid'],
  [/^deal\./, 'error.deal_invalid'],
]

/** What to tell the user about a failed request. */
export function errorMessage(error: unknown): MessageKey {
  if (!(error instanceof ApiError)) return 'error.generic'
  const known = BY_CODE[error.code]
  if (known) return known
  return BY_PREFIX.find(([pattern]) => pattern.test(error.code))?.[1] ?? 'error.generic'
}
