import { INTL_LOCALES, type Locale } from './locale'

/**
 * «21 окт.», or «21 октября» with `long`. Dates are never formatted by hand (ADR-0009).
 * Georgian dates stay numeric, «21.10» and «21.10.2026», because Intl may have no
 * Georgian month names, and a numeral takes Georgian case endings cleanly: «21.10-მდე»
 * (ADR-0015).
 */
export function formatDate(locale: Locale, iso: string, month: 'short' | 'long' = 'short'): string {
  const options: Intl.DateTimeFormatOptions =
    locale === 'ka'
      ? { day: '2-digit', month: '2-digit', year: month === 'long' ? 'numeric' : undefined }
      : { day: 'numeric', month }
  return new Intl.DateTimeFormat(INTL_LOCALES[locale], options).format(new Date(iso))
}
