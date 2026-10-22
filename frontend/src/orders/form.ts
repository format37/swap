import type { OrderDraft, PaymentKind, RateSpec } from '../api/orders'
import type { MessageKey } from '../i18n/ru'
import { parseAmount, parseAmountOrZero, parseRate } from '../money/format'

/** One wanted currency, and its rate as the author types it. */
export interface WantForm {
  currency: string
  country: string
  rate: string
  /** False: «1 {want} = rate {give}». True: «1 {give} = rate {want}». */
  flipped: boolean
  /** Typed by the author. Until then the rate is the market's, and follows the pair (F5). */
  typed: boolean
  /** «Зафиксировать курс» for this currency: off, it follows the market until a proposal
   * locks it (QUESTIONS G2, J1). */
  fixed: boolean
}

/** The wizard's state: strings as typed, until «Опубликовать» (Q-B17: no server drafts). */
export interface OrderForm {
  giveCurrency: string
  giveCountry: string
  total: string
  /** «Только целиком»: one deal takes it all (Q-B5). */
  exact: boolean
  /** Empty or 0: any amount (QUESTIONS F4). */
  least: string
  methods: PaymentKind[]
  /** How the author can be paid, whichever currency they get (QUESTIONS F2). */
  receiveMethods: PaymentKind[]
  from: string
  /** «Ограничить срок»: off, the order is open until its author closes it (F3). */
  limited: boolean
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

/** The pair the way a rate reads best, «1 strong = so many weak»: [base, quote]. */
export function readsAs(giveCurrency: string, currency: string): [string, string] {
  return strength(giveCurrency) < strength(currency)
    ? [giveCurrency, currency]
    : [currency, giveCurrency]
}

/** A new wanted currency, its rate the right way round for the given one. */
export function newWant(giveCurrency: string, currency = '', country = ''): WantForm {
  return {
    currency,
    country,
    rate: '',
    flipped: strength(giveCurrency) < strength(currency),
    typed: false,
    fixed: false,
  }
}

/** The list with `item` taken out if it was in, or added at the end if it wasn't. */
export function toggled<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((other) => other !== item) : [...list, item]
}

export function isoDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function addDays(iso: string, days: number): string {
  const [year = 0, month = 1, day = 1] = iso.split('-').map(Number)
  return isoDate(new Date(year, month - 1, day + days))
}

/** A fresh wizard: from today, with no last day; two weeks if one is asked for (F3). */
export function emptyForm(today: string): OrderForm {
  return {
    giveCurrency: '',
    giveCountry: '',
    total: '',
    exact: false,
    least: '',
    methods: [],
    receiveMethods: [],
    from: today,
    limited: false,
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

/** What is wrong with what is given, if anything: step 1's «Отдаёте». */
export function giveProblem(form: OrderForm, today: string): MessageKey | null {
  if (!form.giveCurrency || !form.giveCountry) return 'wizard.error.choose'
  const total = parseAmount(form.total)
  if (!total) return 'wizard.error.amount'
  if (!form.exact) {
    const least = parseAmountOrZero(form.least)
    if (!least) return 'wizard.error.amount'
    if (cents(least) > cents(total)) return 'wizard.error.range'
  }
  if (form.methods.length === 0) return 'wizard.error.methods'
  if (!form.from) return 'wizard.error.dates'
  if (form.limited && (!form.until || form.until < form.from || form.until < today))
    return 'wizard.error.dates'
  return null
}

/** What is wrong with what is wanted, if anything: step 1's «Получаете». */
export function wantProblem(form: OrderForm): MessageKey | null {
  const seen = new Set<string>()
  for (const want of form.wants) {
    if (!want.currency || !want.country) return 'wizard.error.choose'
    if (want.currency === form.giveCurrency) return 'wizard.error.same'
    // One rate per currency (ADR-0004), so one row per currency.
    if (seen.has(want.currency)) return 'wizard.error.repeated'
    seen.add(want.currency)
    // The market's rate needs nothing typed (QUESTIONS G2).
    if (want.fixed && !parseRate(want.rate)) return 'wizard.error.rate'
  }
  if (form.wants.length === 0) return 'wizard.error.choose'
  return form.receiveMethods.length === 0 ? 'wizard.error.methods' : null
}

/** What is wrong with step 2's «Кому видно», if anything. */
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

/** A wanted currency's rate as the api takes it: the author's own, or the market's (J1). */
export function specOf(giveCurrency: string, want: WantForm): RateSpec {
  return want.fixed
    ? { v: 1, type: 'fixed', quotes: [quoteOf(giveCurrency, want)] }
    : { v: 1, type: 'reference', source: 'coinbase' }
}

/** The order as the api takes it. Call it once every step is right. */
export function toDraft(form: OrderForm): OrderDraft {
  const total = parseAmount(form.total) ?? ''
  return {
    give_currency: form.giveCurrency,
    give_country: form.giveCountry,
    amount_max: total,
    amount_min: form.exact ? total : (parseAmountOrZero(form.least) ?? ''),
    available_from: form.from,
    available_until: form.limited ? form.until : null,
    payout_methods: form.methods,
    receive_methods: form.receiveMethods,
    wants: form.wants.map((want) => ({
      currency: want.currency,
      country: want.country,
      rate_spec: specOf(form.giveCurrency, want),
    })),
    visible_to: form.everyone ? null : form.chosen,
    note: form.note.trim() || null,
  }
}
