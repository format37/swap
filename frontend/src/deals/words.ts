import type { Deal } from '../api/deals'
import { fullName } from '../api/links'
import type { I18n } from '../i18n/context'
import { formatAmount } from '../money/format'
import { nextFor } from './next'

/** The status line as plain text, for lists: «Ждём отправки: 1 712,33 GEL — Alex». */
export function statusText({ t, locale }: I18n, deal: Deal, me: string): string {
  const next = nextFor(deal, me)
  return t(next.line, {
    amount: next.leg ? `${formatAmount(locale, next.leg.amount)} ${next.leg.currency}` : '',
    name: next.waitingFor ? fullName(next.waitingFor) : '',
  })
}
