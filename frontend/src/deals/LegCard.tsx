import { Clock, MapPin, WalletCards } from 'lucide-react'

import type { Leg } from '../api/deals'
import { fullName } from '../api/links'
import { formatDate } from '../i18n/format'
import { useI18n } from '../i18n/useI18n'
import { Money } from '../money/Asset'
import { KINDS } from '../money/kinds'

/**
 * One transfer: who pays whom, how much, how and by when. Where exactly to pay is the
 * parties' own business (QUESTIONS G3).
 */
export function LegCard({ leg }: { leg: Leg }) {
  const { t, locale } = useI18n()
  const kind = KINDS.find((entry) => entry.kind === leg.method)
  const Icon = kind?.icon ?? WalletCards

  return (
    <section className="mx-4 flex flex-col gap-2 rounded-xl bg-section-bg px-4 py-3">
      <p className="text-sm text-hint">
        {t('deal.leg', { seq: leg.seq })} · {fullName(leg.payer)} → {fullName(leg.payee)}
      </p>
      <p className="text-lg">
        <Money locale={locale} amount={leg.amount} code={leg.currency} />
      </p>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="flex items-center gap-1.5">
          <Icon aria-hidden className="size-4 text-accent" />
          {kind ? t(kind.label) : leg.method}
        </span>
        <span className="flex items-center gap-1.5 text-hint">
          <Clock aria-hidden className="size-4" />
          {t('deal.due', { date: formatDate(locale, leg.due_date) })}
        </span>
      </p>

      {leg.method === 'cash' && (
        <p className="flex items-center gap-1.5 text-sm text-hint">
          <MapPin aria-hidden className="size-4" />
          {t('deal.cash')}
        </p>
      )}
    </section>
  )
}
