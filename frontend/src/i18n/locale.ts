export const LOCALES = ['ru', 'en', 'ka'] as const
export type Locale = (typeof LOCALES)[number]
export const DEFAULT_LOCALE: Locale = 'en'

/** Each language's name in its own script, so anyone can find theirs (ADR-0009). */
export const LANGUAGE_NAMES: Record<Locale, string> = {
  ru: 'Русский',
  en: 'English',
  ka: 'ქართული',
}

/**
 * What `Intl` formats numbers and dates with. Desktop Chrome, and so possibly Android's
 * and Windows' WebViews, carries no Georgian data, and Intl then falls back to American
 * English without a word. Georgian writes numbers and numeric dates as Russian does
 * (1 712,33 and 25.10.2026), so it borrows Russian's rules (ADR-0015).
 */
export const INTL_LOCALES: Record<Locale, string> = { ru: 'ru-RU', en: 'en-GB', ka: 'ru-RU' }

export function isLocale(value: unknown): value is Locale {
  return typeof value === 'string' && (LOCALES as readonly string[]).includes(value)
}

/**
 * The api's rule (swap.i18n.resolve_locale): the language picked in the app, else
 * Telegram's, else English. Telegram sends IETF tags, so only the primary subtag counts.
 */
export function resolveLocale(chosen?: string | null, languageCode?: string | null): Locale {
  for (const candidate of [chosen, languageCode?.split('-')[0]?.toLowerCase()]) {
    if (isLocale(candidate)) return candidate
  }
  return DEFAULT_LOCALE
}
