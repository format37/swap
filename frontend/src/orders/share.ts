import type { Order } from '../api/orders'
import type { I18n } from '../i18n/context'
import { countryName } from '../i18n/countries'
import { formatAmount, formatRate } from '../money/format'
import { assetText } from '../money/looks'

/**
 * An order in words, for its author to share in a chat (QUESTIONS O1, ADR-0041), laid out as
 * its row is (N1):
 *
 *   Отдаю 150 000 ₽ RUB · Россия
 *   → 5 136,99 ₾ GEL по 1 GEL = 29,20 RUB
 *   → ≈ 1 842,98 $ USD по рынку
 *   Заявка № 17 в Swap
 *
 * The amounts are the api's (ADR-0004). Its note stays out: it may say where to pay.
 */
export function shareText({ t, locale }: Pick<I18n, 't' | 'locale'>, order: Order): string {
  const money = (amount: string, code: string) =>
    `${formatAmount(locale, amount)} ${assetText(code)}`
  const wants = order.wants.map((want) => {
    const fixed = want.rate_spec.type === 'fixed' ? want.rate_spec.quotes[0] : undefined
    // «≈» while the market sets the rate (G2); the currency alone when it has none now.
    const currency = want.amount
      ? `${fixed ? '' : '≈ '}${money(want.amount, want.currency)}`
      : assetText(want.currency)
    return `→ ${
      fixed
        ? t('wizard.digest.fixed', {
            currency,
            rate: `1 ${fixed.base} = ${formatRate(locale, fixed.value)} ${fixed.quote}`,
          })
        : t('wizard.digest.market', { currency })
    }`
  })
  return [
    t('order.share_gives', {
      amount: money(order.amount_remaining, order.give_currency),
      country: countryName(locale, order.give_country),
    }),
    ...wants,
    t('order.share_number', { number: t('order.number', { n: order.number }) }),
  ].join('\n')
}
