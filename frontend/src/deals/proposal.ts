import type { Proposal } from '../api/deals'
import type { Order, PaymentKind } from '../api/orders'
import type { Locale } from '../i18n/locale'
import type { MessageKey } from '../i18n/ru'
import { formatAmount, parseAmount } from '../money/format'

/** The proposal form's state, strings as typed (ADR-0017). */
export interface ProposalForm {
  amount: string
  want: string
  whole: boolean
  /** How the author pays out: one of the order's ways. */
  giveMethod: PaymentKind | ''
  /** How the proposer pays the other currency: one of the ways the author is paid (F2). */
  counterMethod: PaymentKind | ''
  /** Anything else, such as which bank: the parties settle the rest (QUESTIONS G3). */
  note: string
}

// One way is no choice at all.
function only(kinds: PaymentKind[]): PaymentKind | '' {
  return kinds.length === 1 && kinds[0] ? kinds[0] : ''
}

/** The ways the author takes `currency` in (QUESTIONS L1). */
export function waysFor(order: Order, currency: string): PaymentKind[] {
  return order.wants.find((want) => want.currency === currency)?.receive_methods ?? []
}

/**
 * A fresh proposal for all that remains (QUESTIONS G4). There is no order between the
 * transfers and no dates: the parties settle both themselves (H1).
 */
export function emptyProposal(order: Order, locale: Locale): ProposalForm {
  const want = order.wants[0]?.currency ?? ''
  return {
    amount: formatAmount(locale, order.amount_remaining),
    want,
    whole: false,
    giveMethod: only(order.payout_methods),
    counterMethod: only(waysFor(order, want)),
    note: '',
  }
}

/** Another currency in return: the way to pay stays if the author takes that one so too. */
export function withWant(form: ProposalForm, order: Order, currency: string) {
  const ways = waysFor(order, currency)
  const kept = form.counterMethod && ways.includes(form.counterMethod)
  return { want: currency, counterMethod: kept ? form.counterMethod : only(ways) }
}

function cents(value: string): bigint {
  const [whole = '0', fraction = ''] = value.split('.')
  return BigInt(whole + fraction.padEnd(2, '0'))
}

/** What is wrong with the proposal, if anything; the api checks the same (ADR-0018). */
export function proposalProblem(form: ProposalForm, order: Order): MessageKey | null {
  const amount = parseAmount(form.amount)
  if (!amount) return 'wizard.error.amount'
  if (cents(amount) < cents(order.amount_min) || cents(amount) > cents(order.amount_remaining))
    return 'propose.error.range'
  if (!form.giveMethod) return 'propose.error.their_way'
  if (!form.counterMethod) return 'propose.error.my_way'
  return null
}

/** The proposal as the api takes it. Call it once nothing is wrong. */
export function toProposal(form: ProposalForm): Proposal {
  return {
    amount: parseAmount(form.amount) ?? '',
    want_currency: form.want,
    whole: form.whole,
    give_method: form.giveMethod || 'cash',
    counter_method: form.counterMethod || 'cash',
    note: form.note.trim() || null,
  }
}

/**
 * The slider's bounds and step, in whole units. Whole numbers this size are exact in
 * JavaScript, so the slider never makes a float of an amount; cents are typed.
 */
export function sliderRange(order: Order): { min: number; max: number; step: number } {
  // A minimum of 0 is any amount (F4), but a deal of nothing isn't one.
  const min = Math.max(Math.ceil(Number(order.amount_min)), 1)
  const max = Math.floor(Number(order.amount_remaining))
  const span = Math.max(max - min, 1)
  const step = 10 ** Math.max(0, Math.floor(Math.log10(span)) - 2)
  return { min, max, step }
}
