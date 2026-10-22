import type { Order } from '../api/orders'
import {
  emptyProposal,
  proposalProblem,
  sliderRange,
  toProposal,
  type ProposalForm,
} from './proposal'

const ORDER = {
  amount_min: '10000.00',
  amount_max: '150000.00',
  amount_remaining: '150000.00',
  available_from: '2026-10-25',
  payout_methods: ['bank', 'crypto', 'cash'],
  receive_methods: ['cash', 'bank'],
  wants: [
    { currency: 'GEL', country: 'GE' },
    { currency: 'USD', country: 'GE' },
  ],
} as Order

function filled(changes: Partial<ProposalForm> = {}): ProposalForm {
  return {
    ...emptyProposal(ORDER, 'ru'),
    amount: '50 000',
    giveMethod: 'bank',
    counterMethod: 'cash',
    ...changes,
  }
}

it('starts with all that remains and the first wanted currency', () => {
  const form = emptyProposal(ORDER, 'ru')
  // The whole remainder, as the proposer would type it (QUESTIONS G4).
  expect(form.amount).toBe('150\u00a0000')
  expect(emptyProposal(ORDER, 'en').amount).toBe('150,000')
  expect(form.want).toBe('GEL')
  expect([form.giveMethod, form.counterMethod]).toEqual(['', ''])
  // One way is no choice at all.
  expect(emptyProposal({ ...ORDER, payout_methods: ['cash'] }, 'ru').giveMethod).toBe('cash')
  expect(emptyProposal({ ...ORDER, receive_methods: ['bank'] }, 'ru').counterMethod).toBe('bank')
})

it('turns a filled form into exactly what the api takes', () => {
  expect(toProposal(filled())).toEqual({
    amount: '50000',
    want_currency: 'GEL',
    whole: false,
    give_method: 'bank',
    counter_method: 'cash',
    note: null,
  })
  expect(toProposal(filled({ note: '  Т-Банк  ' })).note).toBe('Т-Банк')
})

it.each<[Partial<ProposalForm>, string]>([
  [{ amount: '' }, 'wizard.error.amount'],
  [{ amount: '9999,99' }, 'propose.error.range'],
  [{ amount: '150000.01' }, 'propose.error.range'],
  [{ giveMethod: '' }, 'propose.error.their_way'],
  [{ counterMethod: '' }, 'propose.error.my_way'],
])('refuses %j', (changes, problem) => {
  expect(proposalProblem(filled(changes), ORDER)).toBe(problem)
})

it('takes exactly the minimum and exactly the remainder', () => {
  expect(proposalProblem(filled({ amount: '10000' }), ORDER)).toBeNull()
  expect(proposalProblem(filled({ amount: '150 000,00' }), ORDER)).toBeNull()
})

it('slides in whole units, in steps that suit the range', () => {
  expect(sliderRange(ORDER)).toEqual({ min: 10000, max: 150000, step: 1000 })
  expect(sliderRange({ ...ORDER, amount_min: '10.50', amount_remaining: '60.00' })).toEqual({
    min: 11,
    max: 60,
    step: 1,
  })
  expect(sliderRange({ ...ORDER, amount_min: '0.00' })).toEqual({ min: 1, max: 150000, step: 1000 })
})
