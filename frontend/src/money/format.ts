import { INTL_LOCALES, type Locale } from '../i18n/locale'

const AMOUNT = /^\d{1,16}(\.\d{1,2})?$/
const RATE = /^\d{1,10}(\.\d{1,10})?$/
const ZERO = /^0*(\.0*)?$/

/**
 * An amount from the api, a decimal string, in the user's language: «150 000», «1 712,33».
 * Intl reads the string as it is, with no float on the way (ADR-0004). Whole amounts drop
 * their cents.
 */
export function formatAmount(locale: Locale, value: string): string {
  const whole = !value.includes('.') || /\.0+$/.test(value)
  return new Intl.NumberFormat(INTL_LOCALES[locale], {
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(value as Intl.StringNumericLiteral)
}

/** A rate as its author typed it, decimals and all: «29,20», «0,0342». */
export function formatRate(locale: Locale, value: string): string {
  const decimals = value.split('.')[1]?.length ?? 0
  return new Intl.NumberFormat(INTL_LOCALES[locale], {
    minimumFractionDigits: decimals,
    maximumFractionDigits: 10,
  }).format(value as Intl.StringNumericLiteral)
}

function plain(text: string): string {
  return text
    .replace(/[\s\u00a0\u202f]/g, '')
    .replace(',', '.')
    .replace(/^0+(?=\d)/, '')
}

/** What someone typed into an amount field, «150 000» or «1712,5», as the api wants it. */
export function parseAmount(text: string): string | null {
  const value = plain(text)
  return AMOUNT.test(value) && !ZERO.test(value) ? value : null
}

/** An amount that may be left empty: blank or zero is '0', as an order's minimum (F4). */
export function parseAmountOrZero(text: string): string | null {
  return ZERO.test(plain(text)) ? '0' : parseAmount(text)
}

/** Whether a decimal string from the api is zero: «0.00». */
export function isZero(value: string): boolean {
  return ZERO.test(value)
}

/** What someone typed into a rate field, «29,20», as the api wants it. */
export function parseRate(text: string): string | null {
  const value = plain(text)
  return RATE.test(value) && !ZERO.test(value) ? value : null
}
