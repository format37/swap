import type { Locale } from '../i18n/locale'
import { Flag } from '../ui/Flag'
import { formatAmount } from './format'
import { look } from './looks'

/** «₽ RUB»: an asset's symbol and code always go together, after its flag (ADR-0003). */
export function Asset({ code }: { code: string }) {
  const { symbol, flag } = look(code)
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      {flag && <Flag code={flag} />}
      {symbol && <span>{symbol}</span>}
      <span>{code}</span>
    </span>
  )
}

/** «150 000 ₽ RUB» with its flag. */
export function Money({ locale, amount, code }: { locale: Locale; amount: string; code: string }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <span className="font-semibold">{formatAmount(locale, amount)}</span>
      <Asset code={code} />
    </span>
  )
}
