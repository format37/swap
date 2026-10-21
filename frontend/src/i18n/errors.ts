import { ApiError } from '../api/client'
import type { MessageKey } from './ru'

// The api's machine codes that have words of their own (ADR-0007).
const BY_CODE: Partial<Record<string, MessageKey>> = {
  init_data_expired: 'error.reopen',
  network: 'error.network',
  'link.not_found': 'error.link_not_found',
  'link.invalid_state': 'error.link_changed',
  'invite.limit': 'error.invite_limit',
}

/** What to tell the user about a failed request. */
export function errorMessage(error: unknown): MessageKey {
  return (error instanceof ApiError && BY_CODE[error.code]) || 'error.generic'
}
