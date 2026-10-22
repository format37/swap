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

const SPACES = /[\s\u00a0\u202f]/g

function plain(text: string): string {
  return text
    .replace(SPACES, '')
    .replace(',', '.')
    .replace(/^0+(?=\d)/, '')
}

/**
 * An amount's digits, with a point for the decimals, however its language writes it
 * (ADR-0040): «150 000», «150,000», «1 712,33», «1,712.33». Money has at most two decimals,
 * so the last comma or point before one or two digits is the decimal point; any other
 * comma groups thousands, three digits each. A point never groups.
 */
function amountDigits(text: string): string | null {
  const squeezed = text.replace(SPACES, '')
  const split = /^(.*)[.,](\d{1,2})$/.exec(squeezed)
  const [whole, cents] = split ? [split[1] ?? '', split[2] ?? ''] : [squeezed, '']
  if (!/^\d+$|^\d{1,3}(,\d{3})+$/.test(whole)) return null
  const digits = whole.replaceAll(',', '').replace(/^0+(?=\d)/, '')
  return cents ? `${digits}.${cents}` : digits
}

/**
 * What someone typed into an amount field, or what the app wrote there, as the api wants
 * it: «1 712,33» and «1,712.33» are both «1712.33» (QUESTIONS M2).
 */
export function parseAmount(text: string): string | null {
  const value = amountDigits(text)
  return value !== null && AMOUNT.test(value) && !ZERO.test(value) ? value : null
}

/** An amount that may be left empty: blank or zero is '0', as an order's minimum (F4). */
export function parseAmountOrZero(text: string): string | null {
  const value = text.replace(SPACES, '') === '' ? '0' : amountDigits(text)
  return value !== null && ZERO.test(value) ? '0' : parseAmount(text)
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
