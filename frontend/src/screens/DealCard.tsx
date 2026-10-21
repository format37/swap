import { Ban, History, Undo2, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useParams } from 'react-router'

import type { Me } from '../api/client'
import { useAccept, useDeal, useStep, type Deal, type DealEvent, type Leg } from '../api/deals'
import { fullName } from '../api/links'
import { usePaymentMethods } from '../api/payments'
import { nextFor } from '../deals/next'
import { LegCard } from '../deals/LegCard'
import { errorMessage } from '../i18n/errors'
import { INTL_LOCALES } from '../i18n/locale'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { formatAmount, formatRate } from '../money/format'
import { confirmAction, hapticNotify, useMainButton } from '../telegram'
import { Avatar } from '../ui/Avatar'
import { Button } from '../ui/Button'
import { Choice } from '../ui/Choice'
import { Loading } from '../ui/Loading'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'
import { Problem } from './Problem'

/**
 * A deal (§11): both legs, a status line that says what to do next, the main action in
 * Telegram's MainButton behind a native confirmation, and the history.
 */
export function DealCard({ me }: { me: Me }) {
  const { id = '' } = useParams()
  const deal = useDeal(id)
  if (deal.isPending)
    return (
      <Screen>
        <Loading />
      </Screen>
    )
  if (deal.isError) return <Problem error={deal.error} retry={() => void deal.refetch()} />
  return <Shown deal={deal.data} me={me} />
}

function Shown({ deal, me }: { deal: Deal; me: Me }) {
  const { t, tn, locale } = useI18n()
  const step = useStep(deal.id)
  const accept = useAccept(deal.id)
  const next = nextFor(deal, me.id)
  const other = deal.role === 'proposer' ? deal.acceptor : deal.proposer
  // The author's own leg, which they receive: it needs their details unless it is cash.
  const theirs = deal.legs.find((leg) => leg.payee.id === me.id && leg.payer.id === other.id)
  const needsDetails = next.main === 'accept' && theirs !== undefined && theirs.method !== 'cash'
  const [receiveWith, setReceiveWith] = useState<string | null>(null)
  const [shown, setShown] = useState<MessageKey | null>(null)
  const failure = step.error ?? accept.error

  const amountText = (leg: Leg) => `${formatAmount(locale, leg.amount)} ${leg.currency}`
  const run = async (question: string, ok: string, action: () => Promise<unknown>) => {
    if (!(await confirmAction(question, ok))) return
    try {
      await action()
      hapticNotify('success')
    } catch {
      hapticNotify('error')
    }
  }

  const leg = next.leg
  useMainButton(
    next.main === 'accept'
      ? {
          text: t('deal.accept'),
          busy: accept.isPending,
          onClick: () => {
            if (needsDetails && !receiveWith) {
              setShown('propose.error.details')
              hapticNotify('error')
              return
            }
            void run(t('deal.accept_confirm'), t('deal.accept'), () =>
              accept.mutateAsync(needsDetails ? receiveWith : null),
            )
          },
        }
      : next.main === 'sent' && leg
        ? {
            text: t('deal.mark_sent'),
            busy: step.isPending,
            onClick: () =>
              void run(
                t('deal.mark_sent_confirm', { amount: amountText(leg) }),
                t('deal.mark_sent'),
                () => step.mutateAsync({ kind: 'sent', seq: leg.seq }),
              ),
          }
        : next.main === 'received' && leg
          ? {
              text: t('deal.mark_received'),
              busy: step.isPending,
              onClick: () =>
                void run(
                  t('deal.mark_received_confirm', { amount: amountText(leg) }),
                  t('deal.mark_received'),
                  () => step.mutateAsync({ kind: 'received', seq: leg.seq }),
                ),
            }
          : null,
  )

  const statusLine = tn(next.line, {
    amount: leg ? <Money locale={locale} amount={leg.amount} code={leg.currency} /> : '',
    name: next.waitingFor ? fullName(next.waitingFor) : '',
  })

  return (
    <Screen>
      <header className="flex items-center gap-3 px-6 pt-4">
        <Avatar name={fullName(other)} />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold">{fullName(other)}</h1>
          <p className="text-sm text-hint">{t('deal.title')}</p>
        </div>
      </header>

      <p className="mx-4 rounded-xl bg-section-bg px-4 py-3 font-medium">{statusLine}</p>
      {deal.status === 'disputed' && deal.dispute_note && (
        <p className="px-6 text-sm whitespace-pre-line text-hint">«{deal.dispute_note}»</p>
      )}

      {deal.legs.map((one) => (
        <LegCard key={one.seq} deal={deal} leg={one} />
      ))}

      <p className="flex flex-wrap items-center gap-1 px-6 text-sm text-hint">
        {tn('deal.rate', {
          rate: (
            <span className="inline-flex items-center gap-1">
              1 <Asset code={deal.rate.base} /> = {formatRate(locale, deal.rate.value)}{' '}
              <Asset code={deal.rate.quote} />
            </span>
          ),
        })}
      </p>

      {needsDetails && (
        <ReceivePicker
          currency={theirs.currency}
          chosen={receiveWith}
          choose={(id) => {
            setShown(null)
            setReceiveWith(id)
          }}
        />
      )}
      {shown && <p className="px-6 text-destructive">{t(shown)}</p>}
      {failure && <p className="px-6 text-destructive">{t(errorMessage(failure))}</p>}

      {next.others.map((kind) => (
        <div key={kind} className="mx-4">
          <Button
            tone="destructive"
            icon={OTHER_ICONS[kind]}
            disabled={step.isPending}
            onClick={() =>
              void run(t(`deal.${kind}_confirm`), t(`deal.${kind}`), () =>
                step.mutateAsync({ kind }),
              )
            }
          >
            {t(`deal.${kind}`)}
          </Button>
        </div>
      ))}

      <Journal deal={deal} />
    </Screen>
  )
}

const OTHER_ICONS: Record<'decline' | 'withdraw' | 'cancel', ReactNode> = {
  decline: <X aria-hidden className="size-5" />,
  withdraw: <Undo2 aria-hidden className="size-5" />,
  cancel: <Ban aria-hidden className="size-5" />,
}

/** Where the author wants their currency, from their saved details (ADR-0010). */
function ReceivePicker({
  currency,
  chosen,
  choose,
}: {
  currency: string
  chosen: string | null
  choose: (id: string) => void
}) {
  const { t, tn } = useI18n()
  const methods = usePaymentMethods()
  const usable = (methods.data ?? []).filter((method) => method.asset === currency)
  return (
    <Section title={t('deal.receive_where', { currency })}>
      {usable.map((method) => (
        <Choice
          key={method.id}
          kind="radio"
          label={`${method.title} · ${method.details?.masked ?? t('details.no_text')}`}
          checked={chosen === method.id}
          onChange={() => {
            choose(method.id)
          }}
        />
      ))}
      {methods.isSuccess && usable.length === 0 && (
        <p className="flex flex-wrap items-center gap-1 px-4 py-3 text-hint">
          {tn('propose.no_details', { currency: <Asset code={currency} /> })}
        </p>
      )}
    </Section>
  )
}

const EVENT_WORDS: Partial<Record<string, MessageKey>> = {
  proposed: 'deal.event.proposed',
  accepted: 'deal.event.accepted',
  declined: 'deal.event.declined',
  withdrawn: 'deal.event.withdrawn',
  expired: 'deal.event.expired',
  cancelled: 'deal.event.cancelled',
  sent: 'deal.event.sent',
  received: 'deal.event.received',
  cancel_requested: 'deal.event.cancel_requested',
  cancel_approved: 'deal.event.cancel_approved',
  cancel_rejected: 'deal.event.cancel_rejected',
  disputed: 'deal.event.disputed',
  resolution_proposed: 'deal.event.resolution_proposed',
  resolved: 'deal.event.resolved',
}

/** The deal's journal, oldest first (FR-4.7). */
function Journal({ deal }: { deal: Deal }) {
  const { t, locale } = useI18n()
  const who = (event: DealEvent) =>
    event.actor_id === deal.proposer.id
      ? fullName(deal.proposer)
      : event.actor_id === deal.acceptor.id
        ? fullName(deal.acceptor)
        : 'Swap'
  const when = new Intl.DateTimeFormat(INTL_LOCALES[locale], {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
  return (
    <Section title={t('deal.journal')}>
      {deal.events.map((event, index) => {
        const key = EVENT_WORDS[event.type]
        return (
          <p key={index} className="flex items-start gap-3 px-4 py-2 text-sm">
            <History aria-hidden className="mt-0.5 size-4 shrink-0 text-hint" />
            <span className="min-w-0 flex-1">
              {key ? t(key, { seq: event.seq ?? '' }) : event.type}
              <span className="text-hint"> · {who(event)}</span>
            </span>
            <span className="shrink-0 text-hint">{when.format(new Date(event.at))}</span>
          </p>
        )
      })}
    </Section>
  )
}
