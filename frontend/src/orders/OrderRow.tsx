import { ArrowRight, ChevronRight } from 'lucide-react'

import { fullName } from '../api/links'
import type { Order } from '../api/orders'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { Avatar } from '../ui/Avatar'
import { orderDates } from './words'

/**
 * One order in a feed (QUESTIONS N1): what is given, on the left, then each wanted currency
 * with what that comes to in it, on the right; then its number, whose it is and when.
 */
export function OrderRow({ order, onOpen }: { order: Order; onOpen: () => void }) {
  const i18n = useI18n()
  const { t, locale } = i18n
  const name = fullName(order.author)
  const status = t(`order.status.${order.status}`)
  // Someone else's order says whose it is, and how it ended once it has (QUESTIONS H4).
  const second = order.mine ? status : order.status === 'open' ? name : `${name} · ${status}`
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-3 px-4 py-3 text-left active:bg-secondary-bg"
    >
      {!order.mine && <Avatar name={name} photo={order.author.photo_url} size="sm" />}
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-x-1.5">
          {/* What remains while it is open; once over, what it was for: «0 RUB» says nothing. */}
          <Money
            locale={locale}
            amount={order.status === 'open' ? order.amount_remaining : order.amount_max}
            code={order.give_currency}
          />
          <ArrowRight aria-hidden className="size-4 text-hint" />
        </span>
        {/* The api works each amount out; «≈» while the market sets the rate (G2). */}
        {order.wants.map((want) => (
          <span key={want.currency} className="flex items-center justify-end gap-1">
            {want.amount ? (
              <>
                {want.rate_spec.type === 'reference' && <span className="text-hint">≈</span>}
                <Money locale={locale} amount={want.amount} code={want.currency} />
              </>
            ) : (
              <Asset code={want.currency} />
            )}
          </span>
        ))}
        <span className="block truncate text-sm text-hint">
          {t('order.number', { n: order.number })} · {second} · {orderDates(i18n, order)}
        </span>
      </span>
      <ChevronRight aria-hidden className="size-5 shrink-0 text-hint" />
    </button>
  )
}
