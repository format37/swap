import { Ban, History, MessageSquareText, Trash2, Undo2, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router'

import type { Me } from '../api/client'
import {
  useAccept,
  useDeal,
  useDeleteDeal,
  useStep,
  type Deal,
  type DealEvent,
  type Leg,
} from '../api/deals'
import { fullName } from '../api/links'
import { nextFor } from '../deals/next'
import { LegCard } from '../deals/LegCard'
import { countryName } from '../i18n/countries'
import { errorMessage } from '../i18n/errors'
import { formatTime } from '../i18n/format'
import { INTL_LOCALES } from '../i18n/locale'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { formatAmount, formatRate } from '../money/format'
import { confirmAction, hapticNotify, useMainButton } from '../telegram'
import { Person } from '../ui/Person'
import { Button } from '../ui/Button'
import { FormError } from '../ui/FormError'
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
  const navigate = useNavigate()
  const step = useStep(deal.id)
  const accept = useAccept(deal.id)
  const remove = useDeleteDeal()
  const next = nextFor(deal, me.id)
  const other = deal.role === 'proposer' ? deal.acceptor : deal.proposer
  const failure = step.error ?? accept.error ?? remove.error
  // Its proposer deletes a finished deal for themselves; its author, the whole order (J3).
  const deletable = deal.role === 'proposer' && FINISHED.includes(deal.status)

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
          // One confirmation and no payment details (QUESTIONS G1).
          onClick: () =>
            void run(t('deal.accept_confirm'), t('deal.accept'), () => accept.mutateAsync()),
        }
      : null,
  )
  // Both transfers run at once, so their marks sit on their own cards (QUESTIONS H2).
  const markOn = (one: Leg) => {
    const mark = next.marks[one.seq]
    if (!mark) return undefined
    return () =>
      void run(
        t(mark === 'sent' ? 'deal.mark_sent_confirm' : 'deal.mark_received_confirm', {
          amount: amountText(one),
        }),
        t(mark === 'sent' ? 'deal.mark_sent' : 'deal.mark_received'),
        () => step.mutateAsync({ kind: mark, seq: one.seq }),
      )
  }

  const statusLine = tn(next.line, {
    amount: leg ? <Money locale={locale} amount={leg.amount} code={leg.currency} /> : '',
    name: next.waitingFor ? fullName(next.waitingFor) : '',
  })

  return (
    <Screen>
      <header className="flex items-center px-6 pt-4">
        <Person
          person={other}
          size="lg"
          heading
          detail={t('deal.on_order', { n: deal.order_number })}
        />
      </header>

      <p className="mx-4 rounded-xl bg-section-bg px-4 py-3 font-medium">{statusLine}</p>
      {deal.status === 'disputed' && deal.dispute_note && (
        <p className="px-6 text-sm whitespace-pre-line text-hint">«{deal.dispute_note}»</p>
      )}

      {deal.legs.map((one) => (
        <LegCard
          key={one.seq}
          leg={one}
          mark={next.marks[one.seq]}
          busy={step.isPending}
          onMark={markOn(one)}
        />
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
        {/* The market's: where it came from, and when it said so (FR-3.5). */}
        {deal.rate.fetched_at && (
          <span>· {t('deal.rate_market', { time: formatTime(locale, deal.rate.fetched_at) })}</span>
        )}
      </p>

      {deal.note && (
        <Section title={t('deal.note')}>
          <p className="flex items-start gap-3 px-4 py-3">
            <MessageSquareText aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
            <span className="min-w-0 flex-1 whitespace-pre-line">{deal.note}</span>
          </p>
        </Section>
      )}
      <FormError>{failure ? t(errorMessage(failure)) : null}</FormError>

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

      {deletable && (
        <div className="mx-4">
          <Button
            tone="destructive"
            icon={<Trash2 aria-hidden className="size-5" />}
            disabled={remove.isPending}
            onClick={() =>
              void run(t('deal.delete_confirm'), t('deal.delete'), async () => {
                await remove.mutateAsync(deal.id)
                // Home: back could lead to the order, gone too if it was the last (M1).
                void navigate('/', { replace: true })
              })
            }
          >
            {t('deal.delete')}
          </Button>
        </div>
      )}

      <Journal deal={deal} />
    </Screen>
  )
}

const FINISHED: Deal['status'][] = ['settled', 'cancelled', 'expired']

const OTHER_ICONS: Record<'decline' | 'withdraw' | 'cancel', ReactNode> = {
  decline: <X aria-hidden className="size-5" />,
  withdraw: <Undo2 aria-hidden className="size-5" />,
  cancel: <Ban aria-hidden className="size-5" />,
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
  // A transfer's line says what moved and where, from its leg (QUESTIONS H3).
  const moved = (seq: number | null | undefined) => {
    const leg = deal.legs.find((one) => one.seq === seq)
    return leg
      ? {
          amount: `${formatAmount(locale, leg.amount)} ${leg.currency}`,
          country: countryName(locale, leg.country),
        }
      : { amount: '', country: '' }
  }
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
              {key ? t(key, moved(event.seq)) : event.type}
              <span className="text-hint"> · {who(event)}</span>
            </span>
            <span className="shrink-0 text-hint">{when.format(new Date(event.at))}</span>
          </p>
        )
      })}
    </Section>
  )
}
