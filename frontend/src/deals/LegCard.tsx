import { CircleCheck, Clock, Copy, MapPin, Pencil, Send, WalletCards } from 'lucide-react'
import { useEffect, useState } from 'react'

import type { Leg } from '../api/deals'
import { fullName } from '../api/links'
import { countryName } from '../i18n/countries'
import { formatDate, formatTime } from '../i18n/format'
import { useI18n } from '../i18n/useI18n'
import { Money } from '../money/Asset'
import { KINDS } from '../money/kinds'
import { copyText, hapticNotify } from '../telegram'
import { Button } from '../ui/Button'
import type { Mark } from './next'

/**
 * One transfer: who pays whom, how much, where and how, and how far it got. Its payee may
 * say where they take it, such as a card number, for the payer to copy (QUESTIONS Q1). The
 * viewer's own mark on it, «Деньги отправлены» or «Деньги получены», sits on the card:
 * both transfers run at once (H2).
 */
export function LegCard({
  leg,
  mark,
  busy = false,
  onMark,
  onDetails,
}: {
  leg: Leg
  mark?: Mark
  busy?: boolean
  onMark?: () => void
  /** Set while the viewer is its payee and may still change where they take it. */
  onDetails?: (details: string) => Promise<unknown>
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
      <Details leg={leg} onSave={onDetails} />
      {mark && (
        <Button tone="filled" disabled={busy} onClick={onMark}>
          {t(mark === 'sent' ? 'deal.mark_sent' : 'deal.mark_received')}
        </Button>
      )}
    </section>
  )
}

/**
 * «Реквизиты»: the payee's words on where to pay, which both sides read and the payer
 * copies in one tap. The payee writes and changes them until the transfer is sent.
 */
function Details({ leg, onSave }: { leg: Leg; onSave?: (details: string) => Promise<unknown> }) {
  const { t } = useI18n()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => {
      setCopied(false)
    }, 2000)
    return () => {
      clearTimeout(timer)
    }
  }, [copied])

  if (editing && onSave)
    return (
      <div className="flex flex-col gap-2">
        <label className="text-sm text-hint">
          {t('details.title')}
          <textarea
            className="mt-1 block min-h-20 w-full resize-none rounded-lg bg-secondary-bg px-3 py-2 text-base text-text outline-none placeholder:text-hint"
            maxLength={500}
            // Opened to type into.
            autoFocus
            placeholder={t('details.placeholder')}
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value)
            }}
          />
        </label>
        <div className="flex gap-2">
          <Button
            tone="filled"
            disabled={saving}
            onClick={() => {
              setSaving(true)
              onSave(draft)
                .then(() => {
                  hapticNotify('success')
                  setEditing(false)
                })
                .catch(() => {
                  hapticNotify('error')
                })
                .finally(() => {
                  setSaving(false)
                })
            }}
          >
            {t('details.save')}
          </Button>
          <Button
            disabled={saving}
            onClick={() => {
              setEditing(false)
            }}
          >
            {t('details.cancel')}
          </Button>
        </div>
      </div>
    )

  const edit = onSave && (
    <button
      type="button"
      onClick={() => {
        setDraft(leg.details ?? '')
        setEditing(true)
      }}
      className="flex items-center gap-1.5 text-sm text-link active:opacity-70"
    >
      <Pencil aria-hidden className="size-4" />
      {t(leg.details ? 'details.edit' : 'details.add')}
    </button>
  )
  if (!leg.details) return edit ?? null
  const details = leg.details
  return (
    <div className="flex flex-col gap-1.5 rounded-lg bg-secondary-bg px-3 py-2">
      <p className="text-sm text-hint">{t('details.title')}</p>
      <p className="break-words whitespace-pre-line select-text">{details}</p>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <button
          type="button"
          onClick={() => {
            void copyText(details).then((ok) => {
              hapticNotify(ok ? 'success' : 'error')
              setCopied(ok)
            })
          }}
          className="flex items-center gap-1.5 text-sm text-link active:opacity-70"
        >
          <Copy aria-hidden className="size-4" />
          {t(copied ? 'details.copied' : 'details.copy')}
        </button>
        {edit}
      </div>
    </div>
  )
}
