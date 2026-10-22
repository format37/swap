import {
  addDays,
  emptyForm,
  giveProblem,
  newWant,
  toDraft,
  wantProblem,
  whoProblem,
  type OrderForm,
} from './form'

const TODAY = '2026-10-22'

function filled(changes: Partial<OrderForm> = {}): OrderForm {
  return {
    ...emptyForm(TODAY),
    giveCurrency: 'RUB',
    giveCountry: 'RU',
    total: '150 000',
    least: '10000',
    methods: ['card', 'phone'],
    wants: [
      { ...newWant('RUB', 'GEL', 'GE'), rate: '29,20' },
      { ...newWant('RUB', 'USD', 'GE'), rate: '81.5' },
    ],
    ...changes,
  }
}

it('starts today, with no last day, and offers two weeks if asked for one', () => {
  const form = emptyForm(TODAY)
  expect(form.from).toBe(TODAY)
  expect(form.limited).toBe(false)
  expect(form.until).toBe('2026-11-05')
  expect(addDays('2026-12-25', 10)).toBe('2027-01-04')
})

it('reads a rate as «1 strong = so many weak», whichever is given', () => {
  expect(newWant('RUB', 'GEL').flipped).toBe(false) // 1 GEL = … RUB
  expect(newWant('GEL', 'RUB').flipped).toBe(true) // 1 GEL = … RUB
  expect(newWant('USD', 'GEL').flipped).toBe(true) // 1 USD = … GEL
})

it('turns a filled wizard into exactly what the api takes', () => {
  expect(toDraft(filled({ note: '  наличные  ' }))).toEqual({
    give_currency: 'RUB',
    give_country: 'RU',
    amount_max: '150000',
    amount_min: '10000',
    available_from: TODAY,
    available_until: null,
    payout_methods: ['card', 'phone'],
    wants: [
      { currency: 'GEL', country: 'GE' },
      { currency: 'USD', country: 'GE' },
    ],
    rate_spec: {
      v: 1,
      type: 'fixed',
      quotes: [
        { base: 'GEL', quote: 'RUB', value: '29.20' },
        { base: 'USD', quote: 'RUB', value: '81.5' },
      ],
    },
    visible_to: null,
    note: 'наличные',
  })
})

it('sends the last day only once it is asked for (F3)', () => {
  expect(toDraft(filled({ limited: true })).available_until).toBe('2026-11-05')
  // A date left behind by switching it off is not sent, and can't stop the wizard.
  const off = filled({ limited: false, until: '2026-10-01' })
  expect(toDraft(off).available_until).toBeNull()
  expect(giveProblem(off, TODAY)).toBeNull()
})

it.each(['', '  ', '0', '0,00'])('reads a minimum of %j as any amount (F4)', (least) => {
  expect(giveProblem(filled({ least }), TODAY)).toBeNull()
  expect(toDraft(filled({ least })).amount_min).toBe('0')
})

it('takes the whole amount as the least one when it goes at once', () => {
  const draft = toDraft(filled({ exact: true, least: '' }))
  expect(draft.amount_min).toBe('150000')
})

it('sends the chosen links only when it isn’t for everyone', () => {
  const ids = ['a0000000-0000-4000-8000-000000000002']
  expect(toDraft(filled({ everyone: false, chosen: ids })).visible_to).toEqual(ids)
})

it.each<[Partial<OrderForm>, string]>([
  [{ giveCountry: '' }, 'wizard.error.choose'],
  [{ total: 'много' }, 'wizard.error.amount'],
  [{ total: '0' }, 'wizard.error.amount'],
  [{ least: 'немного' }, 'wizard.error.amount'],
  [{ least: '-5' }, 'wizard.error.amount'],
  [{ least: '150000.01' }, 'wizard.error.range'],
  [{ methods: [] }, 'wizard.error.methods'],
  [{ from: '' }, 'wizard.error.dates'],
  [{ limited: true, until: '' }, 'wizard.error.dates'],
  [{ limited: true, until: '2026-10-21', from: '2026-10-20' }, 'wizard.error.dates'],
  [{ limited: true, from: '2026-10-30', until: '2026-10-29' }, 'wizard.error.dates'],
])('refuses step 1 with %j', (changes, problem) => {
  expect(giveProblem(filled(changes), TODAY)).toBe(problem)
})

it('lets an exact amount go without a least one', () => {
  expect(giveProblem(filled({ exact: true, least: '' }), TODAY)).toBeNull()
})

it.each<[OrderForm['wants'], string]>([
  [[{ ...newWant('RUB', 'RUB', 'RU'), rate: '1' }], 'wizard.error.same'],
  [[{ ...newWant('RUB', 'GEL', ''), rate: '29' }], 'wizard.error.choose'],
  [[{ ...newWant('RUB', 'GEL', 'GE'), rate: '' }], 'wizard.error.rate'],
  [
    [
      { ...newWant('RUB', 'GEL', 'GE'), rate: '29' },
      { ...newWant('RUB', 'GEL', 'TR'), rate: '29' },
    ],
    'wizard.error.repeated',
  ],
  [[], 'wizard.error.choose'],
])('refuses step 2 with %j', (wants, problem) => {
  expect(wantProblem(filled({ wants }))).toBe(problem)
})

it('wants someone chosen when it isn’t for everyone', () => {
  expect(whoProblem(filled({ everyone: false }))).toBe('wizard.error.who')
  expect(whoProblem(filled())).toBeNull()
})
