import { INTL_LOCALES, type Locale } from './locale'

/**
 * The countries the pickers offer, the region's first. Another is a line here, and the
 * api takes any two capital letters (ADR-0016).
 */
export const COUNTRIES = [
  'RU',
  'GE',
  'AM',
  'AZ',
  'BY',
  'KZ',
  'KG',
  'UZ',
  'TJ',
  'TR',
  'AE',
  'IL',
  'CY',
  'RS',
  'ME',
  'UA',
  'PL',
  'LV',
  'LT',
  'EE',
  'FI',
  'DE',
  'NL',
  'FR',
  'ES',
  'PT',
  'IT',
  'GR',
  'BG',
  'GB',
  'US',
  'CA',
  'TH',
  'VN',
  'ID',
  'IN',
  'CN',
  'KR',
  'JP',
  'AU',
  'EG',
] as const

// Intl may have no Georgian names at all (ADR-0015), so Georgian brings its own.
// Needs a native speaker's read before acceptance, like every Georgian string (ADR-0009).
const GEORGIAN: Record<string, string> = {
  RU: 'რუსეთი',
  GE: 'საქართველო',
  AM: 'სომხეთი',
  AZ: 'აზერბაიჯანი',
  BY: 'ბელარუსი',
  KZ: 'ყაზახეთი',
  KG: 'ყირგიზეთი',
  UZ: 'უზბეკეთი',
  TJ: 'ტაჯიკეთი',
  TR: 'თურქეთი',
  AE: 'არაბთა გაერთიანებული საამიროები',
  IL: 'ისრაელი',
  CY: 'კვიპროსი',
  RS: 'სერბეთი',
  ME: 'მონტენეგრო',
  UA: 'უკრაინა',
  PL: 'პოლონეთი',
  LV: 'ლატვია',
  LT: 'ლიტვა',
  EE: 'ესტონეთი',
  FI: 'ფინეთი',
  DE: 'გერმანია',
  NL: 'ნიდერლანდები',
  FR: 'საფრანგეთი',
  ES: 'ესპანეთი',
  PT: 'პორტუგალია',
  IT: 'იტალია',
  GR: 'საბერძნეთი',
  BG: 'ბულგარეთი',
  GB: 'გაერთიანებული სამეფო',
  US: 'ამერიკის შეერთებული შტატები',
  CA: 'კანადა',
  TH: 'ტაილანდი',
  VN: 'ვიეტნამი',
  ID: 'ინდონეზია',
  IN: 'ინდოეთი',
  CN: 'ჩინეთი',
  KR: 'სამხრეთ კორეა',
  JP: 'იაპონია',
  AU: 'ავსტრალია',
  EG: 'ეგვიპტე',
}

const displayNames = new Map<Locale, Intl.DisplayNames | null>()

function regionNames(locale: Locale): Intl.DisplayNames | null {
  if (!displayNames.has(locale)) {
    let names: Intl.DisplayNames | null = null
    try {
      names = new Intl.DisplayNames([INTL_LOCALES[locale]], { type: 'region' })
    } catch {
      // An old WebView without Intl.DisplayNames: the code it is.
    }
    displayNames.set(locale, names)
  }
  return displayNames.get(locale) ?? null
}

/** «Грузия», «Georgia», «საქართველო»; the code itself when nobody knows better. */
export function countryName(locale: Locale, code: string): string {
  if (locale === 'ka') return GEORGIAN[code] ?? code
  return regionNames(locale)?.of(code) ?? code
}

/** The offered countries, sorted by name in the reader's language. */
export function sortedCountries(locale: Locale): { code: string; name: string }[] {
  return COUNTRIES.map((code) => ({ code, name: countryName(locale, code) })).sort((a, b) =>
    a.name.localeCompare(b.name, locale === 'ka' ? 'ka' : INTL_LOCALES[locale]),
  )
}
