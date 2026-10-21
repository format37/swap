import { Plus } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { usePropose } from '../api/deals'
import { fullName } from '../api/links'
import { useOrder, useQuote, type Order, type PaymentKind, type QuoteRequest } from '../api/orders'
import { usePaymentMethods } from '../api/payments'
import {
  emptyProposal,
  proposalProblem,
  sliderRange,
  toProposal,
  type ProposalForm,
} from '../deals/proposal'
import { errorMessage } from '../i18n/errors'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { parseAmount } from '../money/format'
import { KINDS } from '../money/kinds'
import { isoDate } from '../orders/form'
import { hapticNotify, hapticSelect, useMainButton } from '../telegram'
import { Button } from '../ui/Button'
import { Chip } from '../ui/Chip'
import { Choice } from '../ui/Choice'
import { CONTROL, Field } from '../ui/Field'
import { Loading } from '../ui/Loading'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'
import { Switch } from '../ui/Switch'
import { useDebounced } from '../useDebounced'
import { Problem } from './Problem'

/** «Предложение сделки» on someone's order (FR-4.1, §11). */
export function ProposeDeal() {
  const { id = '' } = useParams()
  const order = useOrder(id)
  if (order.isPending)
    return (
      <Screen>
        <Loading />
      </Screen>
    )
  if (order.isError) return <Problem error={order.error} retry={() => void order.refetch()} />
  return <Form order={order.data} />
}

function Form({ order }: { order: Order }) {
  const { t, tn, locale } = useI18n()
  const navigate = useNavigate()
  const today = useMemo(() => isoDate(new Date()), [])
  const [form, setForm] = useState<ProposalForm>(() => emptyProposal(order, today))
  const [shown, setShown] = useState<MessageKey | null>(null)
  const propose = usePropose(order.id)
  const methods = usePaymentMethods()
  const give = order.give_currency
  const author = fullName(order.author)

  const change = (changes: Partial<ProposalForm>) => {
    setShown(null)
    setForm((current) => ({ ...current, ...changes }))
  }

  const problem = proposalProblem(form, order, today)
  useMainButton({
    text: t('propose.send'),
    busy: propose.isPending,
    onClick: () => {
      if (problem) {
        setShown(problem)
        hapticNotify('error')
        return
      }
      propose.mutate(toProposal(form), {
        onSuccess: (deal) => {
          hapticNotify('success')
          void navigate(`/deals/${deal.id}`, { replace: true })
        },
        onError: () => {
          hapticNotify('error')
        },
      })
    },
  })

  // What the proposer gives back, from the api, which does the arithmetic (ADR-0004).
  const amount = parseAmount(form.amount)
  const request =
    amount && form.want
      ? JSON.stringify({
          amount,
          give_currency: give,
          want_currency: form.want,
          rate_spec: order.rate_spec,
          whole: form.whole,
        })
      : null
  const settled = useDebounced(request)
  const quote = useQuote(
    useMemo(() => (settled ? (JSON.parse(settled) as QuoteRequest) : null), [settled]),
  )

  const slider = sliderRange(order)
  const mine = (methods.data ?? []).filter((method) => method.asset === give)
  const chips = (
    kinds: PaymentKind[],
    chosen: PaymentKind | '',
    pick: (kind: PaymentKind) => void,
  ) => (
    <div className="flex flex-wrap gap-2 p-3">
      {KINDS.filter(({ kind }) => kinds.includes(kind)).map(({ kind, icon, label }) => (
        <Chip
          key={kind}
          icon={icon}
          label={t(label)}
          selected={chosen === kind}
          onToggle={() => {
            hapticSelect()
            pick(kind)
          }}
        />
      ))}
    </div>
  )

  return (
    <Screen>
      <header className="px-6 pt-4">
        <h1 className="text-2xl font-semibold">{t('propose.title')}</h1>
        <p className="text-hint">{author}</p>
      </header>

      <Section title={t('propose.amount')}>
        <Field label={t('wizard.amount')}>
          <span className="flex min-w-0 items-center gap-1.5">
            <input
              className={`${CONTROL} w-full`}
              inputMode="decimal"
              autoComplete="off"
              placeholder="0"
              aria-label={t('propose.amount')}
              value={form.amount}
              onChange={(event) => {
                change({ amount: event.target.value })
              }}
            />
            <span className="shrink-0 text-hint">
              <Asset code={give} />
            </span>
          </span>
        </Field>
        {slider.max > slider.min && (
          <div className="px-4 pt-1 pb-3">
            <input
              type="range"
              className="w-full accent-[var(--color-button)]"
              aria-label={t('propose.amount')}
              min={slider.min}
              max={slider.max}
              step={slider.step}
              value={Math.min(Math.max(Number(amount ?? slider.min), slider.min), slider.max)}
              onChange={(event) => {
                change({ amount: event.target.value })
              }}
            />
            <p className="flex flex-wrap items-center gap-1 text-sm text-hint">
              {tn('order.range', {
                min: <Money locale={locale} amount={order.amount_min} code={give} />,
                max: <Money locale={locale} amount={order.amount_remaining} code={give} />,
              })}
            </p>
          </div>
        )}
      </Section>

      <Section title={t('propose.in_return')}>
        {order.wants.length > 1 && (
          <div className="flex flex-wrap gap-2 p-3">
            {order.wants.map((want) => (
              <button
                key={want.currency}
                type="button"
                aria-pressed={form.want === want.currency}
                onClick={() => {
                  hapticSelect()
                  change({ want: want.currency })
                }}
                className={`rounded-full px-3 py-2 text-sm font-medium ${form.want === want.currency ? 'bg-button text-button-text' : 'bg-secondary-bg'}`}
              >
                <Asset code={want.currency} />
              </button>
            ))}
          </div>
        )}
        {quote.data && amount && (
          <p className="px-4 py-3">
            {tn('propose.result', {
              amount: <Money locale={locale} amount={quote.data.amount} code={form.want} />,
            })}
          </p>
        )}
        <Switch
          label={t('propose.whole')}
          checked={form.whole}
          onChange={(whole) => {
            change({ whole })
          }}
        />
      </Section>

      <Section title={t('propose.their_way', { currency: give })}>
        {chips(order.payout_methods, form.giveMethod, (giveMethod) => {
          change({ giveMethod })
        })}
        {form.giveMethod && form.giveMethod !== 'cash' && (
          <>
            {mine.map((method) => (
              <Choice
                key={method.id}
                kind="radio"
                label={`${method.title} · ${method.details?.masked ?? t('details.no_text')}`}
                checked={form.receiveWith === method.id}
                onChange={() => {
                  change({ receiveWith: method.id })
                }}
              />
            ))}
            {methods.isSuccess && mine.length === 0 && (
              <p className="flex flex-wrap items-center gap-1 px-4 py-2 text-hint">
                {tn('propose.no_details', { currency: <Asset code={give} /> })}
              </p>
            )}
            <div className="p-3">
              <Button
                icon={<Plus aria-hidden className="size-5" />}
                onClick={() => void navigate('/profile/details/new')}
              >
                {t('profile.add_details')}
              </Button>
            </div>
          </>
        )}
      </Section>

      <Section title={t('propose.my_way', { currency: form.want })}>
        {chips(
          KINDS.map(({ kind }) => kind),
          form.counterMethod,
          (counterMethod) => {
            change({ counterMethod })
          },
        )}
      </Section>

      <Section title={t('propose.first')}>
        <Choice
          kind="radio"
          label={t('propose.first_me')}
          checked={form.first === 'proposer'}
          onChange={() => {
            change({ first: 'proposer' })
          }}
        />
        <Choice
          kind="radio"
          label={author}
          checked={form.first === 'author'}
          onChange={() => {
            change({ first: 'author' })
          }}
        />
      </Section>

      <Section title={t('order.when')}>
        <Field label={t('propose.due_mine')}>
          <input
            type="date"
            className={CONTROL}
            min={today}
            value={form.myDue}
            onChange={(event) => {
              change({ myDue: event.target.value })
            }}
          />
        </Field>
        <Field label={t('propose.due_theirs')}>
          <input
            type="date"
            className={CONTROL}
            min={today}
            value={form.theirDue}
            onChange={(event) => {
              change({ theirDue: event.target.value })
            }}
          />
        </Field>
      </Section>

      <p className="px-6 text-sm text-hint">{t('propose.note')}</p>
      {shown && <p className="px-6 text-destructive">{t(shown)}</p>}
      {propose.isError && <p className="px-6 text-destructive">{t(errorMessage(propose.error))}</p>}
    </Screen>
  )
}
