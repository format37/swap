import { Check, Clock, Copy, Lock, MapPin, WalletCards } from 'lucide-react'
import { useState } from 'react'

import type { Deal, Leg } from '../api/deals'
import { fullName } from '../api/links'
import { formatDate } from '../i18n/format'
import { useI18n } from '../i18n/useI18n'
import { Money } from '../money/Asset'
import { KINDS } from '../money/kinds'
import { copyText, hapticNotify } from '../telegram'

/**
 * One transfer: who pays whom, how much, how, by when, and where to. The details show in
 * full to those Q-B8 allows; the api has already decided that.
 */
export function LegCard({ deal, leg }: { deal: Deal; leg: Leg }) {
  const { t, locale } = useI18n()
  const [copied, setCopied] = useState(false)
  const kind = KINDS.find((entry) => entry.kind === leg.method)
  const Icon = kind?.icon ?? WalletCards
  const full = leg.recipient?.full

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

      {leg.recipient ? (
        <div className="flex flex-col gap-1 rounded-lg bg-secondary-bg px-3 py-2 text-sm">
          {leg.recipient.title && <p className="font-medium">{leg.recipient.title}</p>}
          {full ? (
            <>
              <p className="break-words whitespace-pre-line select-all">{full}</p>
              <button
                type="button"
                className="flex items-center gap-1.5 self-start text-link"
                onClick={() => {
                  void copyText(full).then((ok) => {
                    hapticNotify(ok ? 'success' : 'error')
                    setCopied(ok)
                  })
                }}
              >
                {copied ? (
                  <Check aria-hidden className="size-4" />
                ) : (
                  <Copy aria-hidden className="size-4" />
                )}
                {copied ? t('invite.copied') : t('details.copy')}
              </button>
            </>
          ) : leg.recipient.masked ? (
            <p className="flex items-center gap-1.5 text-hint">
              <Lock aria-hidden className="size-4" />
              {leg.recipient.masked} · {t('deal.hidden')}
            </p>
          ) : null}
        </div>
      ) : leg.method === 'cash' ? (
        <p className="flex items-center gap-1.5 text-sm text-hint">
          <MapPin aria-hidden className="size-4" />
          {t('deal.cash')}
        </p>
      ) : (
        deal.status === 'proposed' && <p className="text-sm text-hint">{t('deal.not_chosen')}</p>
      )}

      {(leg.sent_at ?? leg.received_at) && (
        <p className="flex flex-wrap gap-x-3 text-sm text-hint">
          {leg.sent_at && (
            <span className="flex items-center gap-1">
              <Check aria-hidden className="size-4 text-accent" />
              {t('deal.sent_on', { date: formatDate(locale, leg.sent_at) })}
            </span>
          )}
          {leg.received_at && (
            <span className="flex items-center gap-1">
              <Check aria-hidden className="size-4 text-accent" />
              {t('deal.received_on', { date: formatDate(locale, leg.received_at) })}
            </span>
          )}
        </p>
      )}
    </section>
  )
}
