import {
  Banknote,
  Bitcoin,
  CreditCard,
  Ellipsis,
  Landmark,
  Smartphone,
  type LucideIcon,
} from 'lucide-react'

import type { PaymentKind } from '../api/orders'
import type { MessageKey } from '../i18n/ru'

/** How money moves, each with its icon: an order's payout methods, a deal's legs (ADR-0016). */
export const KINDS: { kind: PaymentKind; icon: LucideIcon; label: MessageKey }[] = [
  { kind: 'card', icon: CreditCard, label: 'kind.card' },
  { kind: 'phone', icon: Smartphone, label: 'kind.phone' },
  { kind: 'bank', icon: Landmark, label: 'kind.bank' },
  { kind: 'crypto', icon: Bitcoin, label: 'kind.crypto' },
  { kind: 'cash', icon: Banknote, label: 'kind.cash' },
  { kind: 'other', icon: Ellipsis, label: 'kind.other' },
]
