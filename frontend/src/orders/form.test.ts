import {
  addDays,
  emptyForm,
  giveProblem,
  newWant,
  readsAs,
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
    methods: ['bank', 'crypto'],
    wants: [
      { ...newWant('RUB', 'GEL', 'GE'), receiveMethods: ['cash'], rate: '29,20', fixed: true },
      { ...newWant('RUB', 'USD', 'GE'), receiveMethods: ['cash'], rate: '81.5', fixed: true },
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

it('leaves a new rate to the market until the author types one (F5)', () => {
  expect(newWant('RUB', 'GEL')).toMatchObject({ rate: '', typed: false })
})

it('follows the market unless a currency’s rate is fixed (G2, J1)', () => {
  expect(emptyForm(TODAY).wants[0]?.fixed).toBe(false)
  const market = filled({
    wants: [{ ...newWant('RUB', 'GEL', 'GE'), receiveMethods: ['cash'], rate: '' }],
  })
  // Nothing to type: the market has the rate.
  expect(wantProblem(market)).toBeNull()
  expect(toDraft(market).wants[0]?.rate_spec).toEqual({
    v: 1,
    type: 'reference',
    source: 'coinbase',
  })
  // One currency fixed and one at the market's, side by side.
  const mixed = filled({
    wants: [
      { ...newWant('RUB', 'GEL', 'GE'), receiveMethods: ['cash'], rate: '' },
      { ...newWant('RUB', 'USD', 'GE'), receiveMethods: ['cash'], rate: '80', fixed: true },
    ],
  })
  expect(wantProblem(mixed)).toBeNull()
  expect(toDraft(mixed).wants.map((want) => want.rate_spec)).toEqual([
    { v: 1, type: 'reference', source: 'coinbase' },
    { v: 1, type: 'fixed', quotes: [{ base: 'USD', quote: 'RUB', value: '80' }] },
  ])
})

it('reads a rate as «1 strong = so many weak», whichever is given', () => {
  expect(readsAs('RUB', 'GEL')).toEqual(['GEL', 'RUB'])
  expect(readsAs('USD', 'GEL')).toEqual(['USD', 'GEL'])
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
    payout_methods: ['bank', 'crypto'],
    wants: [
      {
        currency: 'GEL',
        country: 'GE',
        rate_spec: { v: 1, type: 'fixed', quotes: [{ base: 'GEL', quote: 'RUB', value: '29.20' }] },
        receive_methods: ['cash'],
      },
      {
        currency: 'USD',
        country: 'GE',
        rate_spec: { v: 1, type: 'fixed', quotes: [{ base: 'USD', quote: 'RUB', value: '81.5' }] },
        receive_methods: ['cash'],
      },
    ],
    reach: 2,
    visible_to: null,
    repeat_day: null,
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
  expect(toDraft(filled({ reach: 0, chosen: ids }))).toMatchObject({ reach: 0, visible_to: ids })
  // Any other reach sends no list, whatever was ticked before (J2).
  expect(toDraft(filled({ reach: 2, chosen: ids }))).toMatchObject({ reach: 2, visible_to: null })
  expect(toDraft(filled({ reach: null })).reach).toBeNull()
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
])('refuses what is given with %j', (changes, problem) => {
  expect(giveProblem(filled(changes), TODAY)).toBe(problem)
})

it('lets an exact amount go without a least one', () => {
  expect(giveProblem(filled({ exact: true, least: '' }), TODAY)).toBeNull()
})

it.each<[OrderForm['wants'], string]>([
  [[{ ...newWant('RUB', 'RUB', 'RU'), receiveMethods: ['cash'], rate: '1' }], 'wizard.error.same'],
  [[{ ...newWant('RUB', 'GEL', ''), rate: '29' }], 'wizard.error.choose'],
  [
    [{ ...newWant('RUB', 'GEL', 'GE'), receiveMethods: ['cash'], rate: '', fixed: true }],
    'wizard.error.rate',
  ],
  [
    [
      { ...newWant('RUB', 'GEL', 'GE'), receiveMethods: ['cash'], rate: '29' },
      { ...newWant('RUB', 'GEL', 'TR'), receiveMethods: ['cash'], rate: '29' },
    ],
    'wizard.error.repeated',
  ],
  [[], 'wizard.error.choose'],
])('refuses what is wanted with %j', (wants, problem) => {
  expect(wantProblem(filled({ wants }))).toBe(problem)
})

it('wants a way to be paid for every currency (F2, L1)', () => {
  const unpaid = filled({
    wants: filled().wants.map((want) =>
      want.currency === 'USD' ? { ...want, receiveMethods: [] } : want,
    ),
  })
  expect(wantProblem(unpaid)).toBe('wizard.error.methods')
})

it('wants someone chosen when it isn’t for everyone', () => {
  expect(whoProblem(filled({ reach: 0 }))).toBe('wizard.error.who')
  expect(
    whoProblem(filled({ reach: 0, chosen: ['a0000000-0000-4000-8000-000000000002'] })),
  ).toBeNull()
  expect(whoProblem(filled())).toBeNull()
})

it('repeats monthly only when asked, on the day chosen (K7)', () => {
  expect(emptyForm(TODAY)).toMatchObject({ repeats: false, repeatDay: '22' })
  expect(toDraft(filled()).repeat_day).toBeNull()
  expect(toDraft(filled({ repeats: true, repeatDay: '5' })).repeat_day).toBe(5)
})
