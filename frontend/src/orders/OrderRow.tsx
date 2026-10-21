import { ArrowRight, ChevronRight } from 'lucide-react'

import { fullName } from '../api/links'
import type { Order } from '../api/orders'
import { formatDates } from '../i18n/format'
import { useI18n } from '../i18n/useI18n'
import { Asset, Money } from '../money/Asset'
import { Avatar } from '../ui/Avatar'

/** One order in a feed: what remains → what is wanted, and who and when. */
export function OrderRow({ order, onOpen }: { order: Order; onOpen: () => void }) {
  const { t, locale } = useI18n()
  const name = fullName(order.author)
  const wanted = [...new Set(order.wants.map((want) => want.currency))]
  const second = order.mine ? t(`order.status.${order.status}`) : name
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-3 px-4 py-3 text-left active:bg-secondary-bg"
    >
      {!order.mine && <Avatar name={name} size="sm" />}
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
          <Money locale={locale} amount={order.amount_remaining} code={order.give_currency} />
          <ArrowRight aria-hidden className="size-4 text-hint" />
          {wanted.map((code) => (
            <Asset key={code} code={code} />
          ))}
        </span>
        <span className="block truncate text-sm text-hint">
          {second} · {formatDates(locale, order.available_from, order.available_until)}
        </span>
      </span>
      <ChevronRight aria-hidden className="size-5 shrink-0 text-hint" />
    </button>
  )
}
