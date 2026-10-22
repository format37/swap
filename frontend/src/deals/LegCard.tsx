import { CircleCheck, Clock, MapPin, Send, WalletCards } from 'lucide-react'

import type { Leg } from '../api/deals'
import { fullName } from '../api/links'
import { countryName } from '../i18n/countries'
import { formatDate, formatTime } from '../i18n/format'
import { useI18n } from '../i18n/useI18n'
import { Money } from '../money/Asset'
import { KINDS } from '../money/kinds'
import { Button } from '../ui/Button'
import type { Mark } from './next'

/**
 * One transfer: who pays whom, how much, where and how, and how far it got. Where exactly
 * to pay is the parties' own business (QUESTIONS G3). The viewer's own mark on it, «Деньги
 * отправлены» or «Деньги получены», sits on the card: both transfers run at once (H2).
 */
export function LegCard({
  leg,
  mark,
  busy = false,
  onMark,
}: {
  leg: Leg
  mark?: Mark
  busy?: boolean
  onMark?: () => void
}) {
  const { t, locale } = useI18n()
  const kind = KINDS.find((entry) => entry.kind === leg.method)
  const Icon = kind?.icon ?? WalletCards

  return (
    <section className="mx-4 flex flex-col gap-2 rounded-xl bg-section-bg px-4 py-3">
      <p className="text-sm text-hint">
        {fullName(leg.payer)} → {fullName(leg.payee)}
      </p>
      <p className="text-lg">
        <Money locale={locale} amount={leg.amount} code={leg.currency} />
      </p>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="flex items-center gap-1.5">
          <Icon aria-hidden className="size-4 text-accent" />
          {kind ? t(kind.label) : leg.method}
        </span>
        <span className="text-hint">{countryName(locale, leg.country)}</span>
        {/* Deals made before QUESTIONS H1 had a due date. */}
        {leg.due_date && (
          <span className="flex items-center gap-1.5 text-hint">
            <Clock aria-hidden className="size-4" />
            {t('deal.due', { date: formatDate(locale, leg.due_date) })}
          </span>
        )}
      </p>

      {leg.method === 'cash' && (
        <p className="flex items-center gap-1.5 text-sm text-hint">
          <MapPin aria-hidden className="size-4" />
          {t('deal.cash')}
        </p>
      )}
      {leg.received_at ? (
        <p className="flex items-center gap-1.5 text-sm text-accent">
          <CircleCheck aria-hidden className="size-4" />
          {t('deal.received_at', { time: formatTime(locale, leg.received_at) })}
        </p>
      ) : (
        leg.sent_at && (
          <p className="flex items-center gap-1.5 text-sm text-hint">
            <Send aria-hidden className="size-4" />
            {t('deal.sent_at', { time: formatTime(locale, leg.sent_at) })}
          </p>
        )
      )}
      {mark && (
        <Button tone="filled" disabled={busy} onClick={onMark}>
          {t(mark === 'sent' ? 'deal.mark_sent' : 'deal.mark_received')}
        </Button>
      )}
    </section>
  )
}
