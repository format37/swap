import { CalendarDays, Eye, Lock, MessageSquareText } from 'lucide-react'
import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router'

import { fullName } from '../api/links'
import type { Me } from '../api/client'
import { useDeals } from '../api/deals'
import { useCloseOrder, useOrder, type Order } from '../api/orders'
import { DealRow } from '../deals/DealRow'
import { countryName } from '../i18n/countries'
import { errorMessage } from '../i18n/errors'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { formatRate, isZero } from '../money/format'
import { KINDS } from '../money/kinds'
import { orderDates } from '../orders/words'
import { confirmAction, hapticNotify, useMainButton } from '../telegram'
import { Avatar } from '../ui/Avatar'
import { Button } from '../ui/Button'
import { Loading } from '../ui/Loading'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'
import { Problem } from './Problem'

/** An order: what, how much remains, for what, how, when, and who sees it (§11). */
export function OrderCard({ me }: { me: Me }) {
  const { id = '' } = useParams()
  const order = useOrder(id)
  if (order.isPending)
    return (
      <Screen>
        <Loading />
      </Screen>
    )
  if (order.isError) return <Problem error={order.error} retry={() => void order.refetch()} />
  return <Shown order={order.data} me={me} />
}

function Row({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <span aria-hidden className="mt-0.5 shrink-0 text-accent">
        {icon}
      </span>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}

function Shown({ order, me }: { order: Order; me: Me }) {
  const i18n = useI18n()
  const { t, tn, locale } = i18n
  const navigate = useNavigate()
  const close = useCloseOrder()
  const deals = useDeals('active', order.id)

  // Someone else's open order: the main action is a proposal (§11).
  useMainButton(
    !order.mine && order.status === 'open'
      ? { text: t('order.propose'), onClick: () => void navigate(`/orders/${order.id}/propose`) }
      : null,
  )
  const name = fullName(order.author)
  const give = order.give_currency
  const money = (amount: string) => <Money locale={locale} amount={amount} code={give} />
  const exact = order.amount_min === order.amount_max

  return (
    <Screen>
      <header className="flex items-center gap-3 px-6 pt-4">
        <Avatar name={name} />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold">{name}</h1>
          <p className="truncate text-sm text-hint">
            {order.author.username ? `@${order.author.username} · ` : ''}
            {t(`order.status.${order.status}`)}
          </p>
        </div>
      </header>

      <Section title={order.mine ? t('order.i_give') : t('order.gives')}>
        <div className="flex flex-col gap-1 px-4 py-3">
          <p className="flex flex-wrap items-center gap-x-1.5 text-lg">
            {tn('order.remaining', { amount: money(order.amount_remaining) })}
          </p>
          <p className="text-sm text-hint">
            {countryName(locale, order.give_country)}
            {exact && <> · {tn('order.exactly', { amount: money(order.amount_max) })}</>}
            {/* A minimum of 0 is any amount, which goes without saying (F4). */}
            {!exact && !isZero(order.amount_min) && (
              <> · {tn('order.min_deal', { amount: money(order.amount_min) })}</>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 px-4 pb-3">
          {KINDS.filter(({ kind }) => order.payout_methods.includes(kind)).map(
            ({ kind, icon: Icon, label }) => (
              <span
                key={kind}
                className="flex items-center gap-1.5 rounded-full bg-secondary-bg px-3 py-1.5 text-sm"
              >
                <Icon aria-hidden className="size-4 text-accent" />
                {t(label)}
              </span>
            ),
          )}
        </div>
        <Row icon={<CalendarDays className="size-5" />}>{orderDates(i18n, order)}</Row>
      </Section>

      <Section title={order.mine ? t('order.i_want') : t('order.wants')}>
        {order.wants.map((want) => {
          const quote = order.rate_spec.quotes.find(
            (q) => q.base === want.currency || q.quote === want.currency,
          )
          return (
            <div
              key={`${want.currency}-${want.country}`}
              className="flex flex-col gap-0.5 px-4 py-3"
            >
              <p className="flex flex-wrap items-center gap-x-2">
                <Asset code={want.currency} />
                <span className="text-hint">· {countryName(locale, want.country)}</span>
              </p>
              {quote && (
                <p className="flex flex-wrap items-center gap-1 text-sm text-hint">
                  {t('order.rate')}: 1 <Asset code={quote.base} /> ={' '}
                  {formatRate(locale, quote.value)} <Asset code={quote.quote} />
                </p>
              )}
            </div>
          )
        })}
      </Section>

      {order.note && (
        <Section title={t('order.note')}>
          <Row icon={<MessageSquareText className="size-5" />}>
            <p className="whitespace-pre-line">{order.note}</p>
          </Row>
        </Section>
      )}

      {order.visibility && (
        <Section>
          <Row icon={<Eye className="size-5" />}>
            {order.visibility.all_links
              ? t('order.visible_all')
              : t('order.visible_some', {
                  names: order.visibility.people.map(fullName).join(', '),
                })}
          </Row>
        </Section>
      )}

      {deals.data && deals.data.length > 0 && (
        <Section title={t('order.deals')}>
          {deals.data.map((deal) => (
            <DealRow
              key={deal.id}
              deal={deal}
              me={me.id}
              onOpen={() => void navigate(`/deals/${deal.id}`)}
            />
          ))}
        </Section>
      )}

      {order.mine && order.status === 'open' && (
        <div className="mx-4">
          <Button
            tone="destructive"
            icon={<Lock aria-hidden className="size-5" />}
            disabled={close.isPending}
            onClick={() => {
              void confirmAction(t('order.close_confirm'), t('order.close'), {
                destructive: true,
              }).then((confirmed) => {
                if (!confirmed) return
                close.mutate(order.id, {
                  onSuccess: () => {
                    hapticNotify('success')
                    void navigate(-1)
                  },
                  onError: () => {
                    hapticNotify('error')
                  },
                })
              })
            }}
          >
            {t('order.close')}
          </Button>
        </div>
      )}
      {close.isError && <p className="px-6 text-destructive">{t(errorMessage(close.error))}</p>}
    </Screen>
  )
}
