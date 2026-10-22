import { Banknote, Bitcoin, Landmark, type LucideIcon } from 'lucide-react'

import type { PaymentKind } from '../api/orders'
import type { MessageKey } from '../i18n/ru'

/**
 * How money moves, each with its icon: an order's ways, a deal's legs (ADR-0016). Three,
 * as the owner put it, «нал, банк или крипта» (QUESTIONS G3, ADR-0021).
 */
export const KINDS: { kind: PaymentKind; icon: LucideIcon; label: MessageKey }[] = [
  { kind: 'cash', icon: Banknote, label: 'kind.cash' },
  { kind: 'bank', icon: Landmark, label: 'kind.bank' },
  { kind: 'crypto', icon: Bitcoin, label: 'kind.crypto' },
]
