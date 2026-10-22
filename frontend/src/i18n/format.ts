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
  return new Intl.DateTimeFormat(INTL_LOCALES[locale], options).format(toDate(iso))
}

/**
 * A calendar date, «2026-10-25», is that day where the reader is. `new Date()` would take
 * it as midnight UTC, which is the day before anywhere west of Greenwich.
 */
function toDate(iso: string): Date {
  const day = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  return day ? new Date(Number(day[1]), Number(day[2]) - 1, Number(day[3])) : new Date(iso)
}

/** «14:05» today, «21.10, 14:05» on another day: when a rate was taken (§11). */
export function formatTime(locale: Locale, iso: string, now: Date = new Date()): string {
  const at = new Date(iso)
  const options: Intl.DateTimeFormatOptions =
    at.toDateString() === now.toDateString()
      ? { hour: '2-digit', minute: '2-digit' }
      : { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }
  return new Intl.DateTimeFormat(INTL_LOCALES[locale], options).format(at)
}

/** «25 окт. – 8 нояб.», «25.10 – 08.11». */
export function formatDates(locale: Locale, from: string, until: string): string {
  return `${formatDate(locale, from)} – ${formatDate(locale, until)}`
}
