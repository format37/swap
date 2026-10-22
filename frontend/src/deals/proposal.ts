import type { Proposal } from '../api/deals'
import type { Order, PaymentKind } from '../api/orders'
import type { MessageKey } from '../i18n/ru'
import { parseAmount } from '../money/format'
import { addDays } from '../orders/form'

/** The proposal form's state, strings as typed (ADR-0017). */
export interface ProposalForm {
  amount: string
  want: string
  whole: boolean
  first: 'proposer' | 'author'
  /** How the author pays out: one of the order's ways. */
  giveMethod: PaymentKind | ''
  /** How the proposer pays the other currency: one of the ways the author is paid (F2). */
  counterMethod: PaymentKind | ''
  myDue: string
  theirDue: string
  /** Anything else, such as which bank: the parties settle the rest (QUESTIONS G3). */
  note: string
}

/** A fresh proposal: the proposer first (Q-B16), a day apart from when the order starts. */
export function emptyProposal(order: Order, today: string): ProposalForm {
  const start = order.available_from > today ? order.available_from : today
  // One way is no choice at all.
  const only = (kinds: PaymentKind[]) => (kinds.length === 1 && kinds[0] ? kinds[0] : '')
  return {
    amount: '',
    want: order.wants[0]?.currency ?? '',
    whole: false,
    first: 'proposer',
    giveMethod: only(order.payout_methods),
    counterMethod: only(order.receive_methods),
    myDue: addDays(start, 1),
    theirDue: addDays(start, 3),
    note: '',
  }
}

function cents(value: string): bigint {
  const [whole = '0', fraction = ''] = value.split('.')
  return BigInt(whole + fraction.padEnd(2, '0'))
}

/** What is wrong with the proposal, if anything; the api checks the same (ADR-0018). */
export function proposalProblem(
  form: ProposalForm,
  order: Order,
  today: string,
): MessageKey | null {
  const amount = parseAmount(form.amount)
  if (!amount) return 'wizard.error.amount'
  if (cents(amount) < cents(order.amount_min) || cents(amount) > cents(order.amount_remaining))
    return 'propose.error.range'
  if (!form.giveMethod) return 'propose.error.their_way'
  if (!form.counterMethod) return 'propose.error.my_way'
  if (form.myDue < today || form.theirDue < today) return 'propose.error.dates'
  return null
}

/** The proposal as the api takes it. Call it once nothing is wrong. */
export function toProposal(form: ProposalForm): Proposal {
  return {
    amount: parseAmount(form.amount) ?? '',
    want_currency: form.want,
    whole: form.whole,
    first: form.first,
    give_method: form.giveMethod || 'cash',
    counter_method: form.counterMethod || 'cash',
    my_due: form.myDue,
    their_due: form.theirDue,
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
