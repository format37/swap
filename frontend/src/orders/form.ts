import type { OrderDraft, PaymentKind } from '../api/orders'
import type { MessageKey } from '../i18n/ru'
import { parseAmount, parseRate } from '../money/format'

/** One wanted currency, and its rate as the author types it. */
export interface WantForm {
  currency: string
  country: string
  rate: string
  /** False: «1 {want} = rate {give}». True: «1 {give} = rate {want}». */
  flipped: boolean
}

/** The wizard's state: strings as typed, until «Опубликовать» (Q-B17: no server drafts). */
export interface OrderForm {
  giveCurrency: string
  giveCountry: string
  total: string
  /** «Только целиком»: one deal takes it all (Q-B5). */
  exact: boolean
  least: string
  methods: PaymentKind[]
  from: string
  until: string
  wants: WantForm[]
  everyone: boolean
  chosen: string[]
  note: string
}

// Roughly how much one unit is worth, the strongest first. A rate reads best as «1 strong
// = so many weak»: «1 GEL = 29,20 RUB», whichever of the two is given.
const STRENGTH = ['EUR', 'USD', 'USDC', 'USDT', 'GEL', 'TRY', 'RUB', 'AMD', 'KZT']

function strength(code: string): number {
  const rank = STRENGTH.indexOf(code)
  return rank === -1 ? STRENGTH.length : rank
}

/** A new wanted currency, its rate the right way round for the given one. */
export function newWant(giveCurrency: string, currency = '', country = ''): WantForm {
  return {
    currency,
    country,
    rate: '',
    flipped: strength(giveCurrency) < strength(currency),
  }
}

export function isoDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function addDays(iso: string, days: number): string {
  const [year = 0, month = 1, day = 1] = iso.split('-').map(Number)
  return isoDate(new Date(year, month - 1, day + days))
}

/** A fresh wizard: from today, for two weeks (Q-B17). */
export function emptyForm(today: string): OrderForm {
  return {
    giveCurrency: '',
    giveCountry: '',
    total: '',
    exact: false,
    least: '',
    methods: [],
    from: today,
    until: addDays(today, 14),
    wants: [newWant('')],
    everyone: true,
    chosen: [],
    note: '',
  }
}

/** Compares two decimal strings exactly, without a float: in cents, as bigints. */
function cents(value: string): bigint {
  const [whole = '0', fraction = ''] = value.split('.')
  return BigInt(whole + fraction.padEnd(2, '0'))
}

/** What is wrong with step 1, «Отдаю», if anything. */
export function giveProblem(form: OrderForm, today: string): MessageKey | null {
  if (!form.giveCurrency || !form.giveCountry) return 'wizard.error.choose'
  const total = parseAmount(form.total)
  if (!total) return 'wizard.error.amount'
  if (!form.exact) {
    const least = parseAmount(form.least)
    if (!least) return 'wizard.error.amount'
    if (cents(least) > cents(total)) return 'wizard.error.range'
  }
  if (form.methods.length === 0) return 'wizard.error.methods'
  if (!form.from || !form.until || form.until < form.from || form.until < today)
    return 'wizard.error.dates'
  return null
}

/** What is wrong with step 2, «Хочу», if anything. */
export function wantProblem(form: OrderForm): MessageKey | null {
  const seen = new Set<string>()
  for (const want of form.wants) {
    if (!want.currency || !want.country) return 'wizard.error.choose'
    if (want.currency === form.giveCurrency) return 'wizard.error.same'
    // One rate per currency (ADR-0004), so one row per currency.
    if (seen.has(want.currency)) return 'wizard.error.repeated'
    seen.add(want.currency)
    if (!parseRate(want.rate)) return 'wizard.error.rate'
  }
  return form.wants.length === 0 ? 'wizard.error.choose' : null
}

/** What is wrong with step 3, «Кому видно», if anything. */
export function whoProblem(form: OrderForm): MessageKey | null {
  return form.everyone || form.chosen.length > 0 ? null : 'wizard.error.who'
}

/** «1 GEL = 29.20 RUB» as the api's quote. */
export function quoteOf(giveCurrency: string, want: WantForm) {
  const value = parseRate(want.rate) ?? ''
  return want.flipped
    ? { base: giveCurrency, quote: want.currency, value }
    : { base: want.currency, quote: giveCurrency, value }
}

/** The order as the api takes it. Call it once every step is right. */
export function toDraft(form: OrderForm): OrderDraft {
  const total = parseAmount(form.total) ?? ''
  return {
    give_currency: form.giveCurrency,
    give_country: form.giveCountry,
    amount_max: total,
    amount_min: form.exact ? total : (parseAmount(form.least) ?? ''),
    available_from: form.from,
    available_until: form.until,
    payout_methods: form.methods,
    wants: form.wants.map(({ currency, country }) => ({ currency, country })),
    rate_spec: {
      v: 1,
      type: 'fixed',
      quotes: form.wants.map((want) => quoteOf(form.giveCurrency, want)),
    },
    visible_to: form.everyone ? null : form.chosen,
    note: form.note.trim() || null,
  }
}
