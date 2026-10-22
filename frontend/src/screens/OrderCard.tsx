import {
  CalendarDays,
  Eye,
  Repeat,
  Lock,
  MessageSquareText,
  RotateCcw,
  Repeat2,
  Trash2,
  Waypoints,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router'

import { fullName } from '../api/links'
import type { Me } from '../api/client'
import { useDeals, type Deal } from '../api/deals'
import {
  useCloseOrder,
  useDeleteOrder,
  useMarketRate,
  useOrder,
  useReopenOrder,
  useStopRepeating,
  type Order,
  type PaymentKind,
} from '../api/orders'
import { DealRow } from '../deals/DealRow'
import { countryName } from '../i18n/countries'
import { errorMessage } from '../i18n/errors'
import { formatTime } from '../i18n/format'
import type { MessageKey } from '../i18n/ru'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { formatRate, isZero } from '../money/format'
import { KINDS } from '../money/kinds'
import { readsAs } from '../orders/form'
import { orderDates } from '../orders/words'
import { confirmAction, hapticNotify, useMainButton } from '../telegram'
import { Button } from '../ui/Button'
import { Loading } from '../ui/Loading'
import { Person } from '../ui/Person'
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

/** The market's rate of this moment for an order that follows it (QUESTIONS G2). */
function MarketRate({ give, want }: { give: string; want: string }) {
  const { t, tn, locale } = useI18n()
  const [base, quote] = readsAs(give, want)
  const market = useMarketRate(base, quote).data
  return (
    <p className="flex flex-wrap items-center gap-1 text-sm text-hint">
      {tn('order.rate_market', {
        rate: market ? (
          <>
            1 <Asset code={base} /> = {formatRate(locale, market.value)} <Asset code={quote} />
          </>
        ) : (
          '…'
        ),
      })}
      {market && (
        <span>· {t('order.market_source', { time: formatTime(locale, market.fetched_at) })}</span>
      )}
    </p>
  )
}

/** The ways money can move, as plain pills: «Наличные», «Банк». */
function Methods({ kinds, inset = true }: { kinds: PaymentKind[]; inset?: boolean }) {
  const { t } = useI18n()
  return (
    <div className={`flex flex-wrap gap-2 ${inset ? 'px-4 py-3' : 'pt-1.5'}`}>
      {KINDS.filter(({ kind }) => kinds.includes(kind)).map(({ kind, icon: Icon, label }) => (
        <span
          key={kind}
          className="flex items-center gap-1.5 rounded-full bg-secondary-bg px-3 py-1.5 text-sm"
        >
          <Icon aria-hidden className="size-4 text-accent" />
          {t(label)}
        </span>
      ))}
    </div>
  )
}

function running(deal: Deal): boolean {
  return ['proposed', 'accepted', 'disputed'].includes(deal.status)
}

function Shown({ order, me }: { order: Order; me: Me }) {
  const i18n = useI18n()
  const { t, tn, locale } = i18n
  const navigate = useNavigate()
  const close = useCloseOrder()
  const reopen = useReopenOrder()
  const remove = useDeleteOrder()
  const stop = useStopRepeating()
  // Finished deals too: the order's card is its history (QUESTIONS H4).
  const deals = useDeals('all', order.id)

  // Someone else's open order: the main action is a proposal (§11).
  useMainButton(
    !order.mine && order.status === 'open'
      ? { text: t('order.propose'), onClick: () => void navigate(`/orders/${order.id}/propose`) }
      : null,
  )
  const give = order.give_currency
  const money = (amount: string) => <Money locale={locale} amount={amount} code={give} />
  const exact = order.amount_min === order.amount_max

  return (
    <Screen>
      <header className="flex items-center px-6 pt-4">
        <Person
          person={order.author}
          size="lg"
          heading
          detail={`${t('order.number', { n: order.number })} · ${t(`order.status.${order.status}`)}`}
        />
      </header>

      {/* How this viewer reaches its author, their own link first (QUESTIONS J2). */}
      {order.chain && order.chain.length > 0 && (
        <p className="flex items-center gap-2 px-6 text-sm text-hint">
          <Waypoints aria-hidden className="size-4 shrink-0 text-accent" />
          {t('order.chain', { names: order.chain.map(fullName).join(' → ') })}
        </p>
      )}

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
        <Methods kinds={order.payout_methods} />
        <Row icon={<CalendarDays className="size-5" />}>{orderDates(i18n, order)}</Row>
        {/* A copy goes out every month on this day (QUESTIONS K7). */}
        {order.repeat_day && (
          <Row icon={<Repeat className="size-5" />}>
            {t('order.repeats', { day: order.repeat_day })}
          </Row>
        )}
      </Section>

      <Section title={order.mine ? t('order.i_want') : t('order.wants')}>
        {order.wants.map((want) => {
          // Each currency has its own rate: the author's, or the market's (QUESTIONS J1).
          const quote = want.rate_spec.type === 'fixed' ? want.rate_spec.quotes[0] : undefined
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
              {want.rate_spec.type === 'reference' && (
                <MarketRate give={order.give_currency} want={want.currency} />
              )}
              {/* How the author takes this currency (QUESTIONS L1). */}
              <Methods kinds={want.receive_methods} inset={false} />
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
            {order.visibility.reach === 0
              ? t('order.visible_some', {
                  names: order.visibility.people.map(fullName).join(', '),
                })
              : t(`order.reach.${order.visibility.reach ?? 'all'}` as MessageKey)}
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
      {/* A closed order can open again as it was (F7); any that isn't open can go (F6). */}
      {order.mine && order.status === 'closed' && (
        <div className="mx-4">
          <Button
            icon={<RotateCcw aria-hidden className="size-5" />}
            disabled={reopen.isPending}
            onClick={() => {
              reopen.mutate(order.id, {
                onSuccess: () => {
                  hapticNotify('success')
                },
                onError: () => {
                  hapticNotify('error')
                },
              })
            }}
          >
            {t('order.reopen')}
          </Button>
        </div>
      )}
      {/* Only once nothing on it runs. The author deletes it with all its deals (J3), and
          whoever dealt on it deletes all their own deals on it (L4). */}
      {deals.data &&
        !deals.data.some(running) &&
        (order.mine ? order.status !== 'open' : deals.data.length > 0) && (
          <div className="mx-4">
            <Button
              tone="destructive"
              icon={<Trash2 aria-hidden className="size-5" />}
              disabled={remove.isPending}
              onClick={() => {
                const [question, action] = order.mine
                  ? (['order.delete_confirm', 'order.delete'] as const)
                  : (['order.delete_mine_confirm', 'order.delete_mine'] as const)
                void confirmAction(t(question), t(action), {
                  destructive: true,
                }).then((confirmed) => {
                  if (!confirmed) return
                  remove.mutate(order.id, {
                    onSuccess: () => {
                      hapticNotify('success')
                      // Home: back could lead to a deal or a list it was in (QUESTIONS M1).
                      void navigate('/', { replace: true })
                    },
                    onError: () => {
                      hapticNotify('error')
                    },
                  })
                })
              }}
            >
              {t(order.mine ? 'order.delete' : 'order.delete_mine')}
            </Button>
          </div>
        )}
      {order.mine && order.repeat_day && (
        <div className="mx-4">
          <Button
            icon={<Repeat2 aria-hidden className="size-5" />}
            disabled={stop.isPending}
            onClick={() => {
              void confirmAction(t('order.stop_repeating_confirm'), t('order.stop_repeating')).then(
                (confirmed) => {
                  if (confirmed) stop.mutate(order.id)
                },
              )
            }}
          >
            {t('order.stop_repeating')}
          </Button>
        </div>
      )}
      {[close, reopen, remove, stop].map(
        (action, index) =>
          action.isError && (
            <p key={index} className="px-6 text-destructive">
              {t(errorMessage(action.error))}
            </p>
          ),
      )}
    </Screen>
  )
}
