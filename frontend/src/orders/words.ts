import type { Order } from '../api/orders'
import type { I18n } from '../i18n/context'
import { formatDate, formatDates } from '../i18n/format'

/** «25 окт. – 8 нояб.», or «с 25 окт., без срока» when it has no last day (F3). */
export function orderDates(
  { t, locale }: I18n,
  order: Pick<Order, 'available_from' | 'available_until'>,
): string {
  return order.available_until
    ? formatDates(locale, order.available_from, order.available_until)
    : t('order.since', { date: formatDate(locale, order.available_from) })
}
