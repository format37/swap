import { formatAmount, formatRate, parseAmount, parseAmountOrZero, parseRate } from './format'

const NBSP = '\u00a0'

it('writes amounts the reader’s way, and drops whole cents', () => {
  expect(formatAmount('ru', '150000.00')).toBe(`150${NBSP}000`)
  expect(formatAmount('ru', '1712.33')).toBe(`1${NBSP}712,33`)
  expect(formatAmount('en', '1712.30')).toBe('1,712.30')
  // Georgian borrows Russian's separators (ADR-0015).
  expect(formatAmount('ka', '1712.33')).toBe(`1${NBSP}712,33`)
})

it('keeps every digit of a big amount', () => {
  expect(formatAmount('en', '9999999999999999.99')).toBe('9,999,999,999,999,999.99')
})

it('writes a rate with its decimals', () => {
  expect(formatRate('ru', '29.20')).toBe('29,20')
  expect(formatRate('en', '0.0342465753')).toBe('0.0342465753')
})

it.each([
  ['150000', '150000'],
  ['150 000', '150000'],
  [`150${NBSP}000`, '150000'],
  ['1712,5', '1712.5'],
  ['1712.50', '1712.50'],
  ['007', '7'],
  // English groups with commas, and its decimals follow a point (QUESTIONS M2).
  ['150,000', '150000'],
  ['1,712.33', '1712.33'],
  ['9,999,999.5', '9999999.5'],
  [`1${NBSP}712,33`, '1712.33'],
  ['0', null],
  ['0,00', null],
  ['', null],
  // A point never groups, and a comma groups three digits (ADR-0040).
  ['12.345', null],
  ['1.712,33', null],
  ['1,2345', null],
  ['12,34,567', null],
  ['-5', null],
  ['1e3', null],
  ['abc', null],
])('reads the amount %j as %j', (typed, expected) => {
  expect(parseAmount(typed)).toBe(expected)
})

it.each(['ru', 'en', 'ka'] as const)('reads back every amount it writes in %s', (locale) => {
  const written: [string, string][] = [
    ['150000.00', '150000'],
    ['2920.00', '2920'],
    ['1712.33', '1712.33'],
    ['0.50', '0.50'],
    ['9999999999999999.99', '9999999999999999.99'],
  ]
  for (const [value, digits] of written) {
    expect(parseAmount(formatAmount(locale, value))).toBe(digits)
  }
})

it('takes a blank or zero minimum as 0, and refuses one it can’t read', () => {
  expect(parseAmountOrZero('')).toBe('0')
  expect(parseAmountOrZero(NBSP)).toBe('0')
  expect(parseAmountOrZero('0,00')).toBe('0')
  expect(parseAmountOrZero('10,000')).toBe('10000')
  expect(parseAmountOrZero('abc')).toBeNull()
})

it('reads a rate with up to ten decimals', () => {
  expect(parseRate('29,20')).toBe('29.20')
  expect(parseRate('0.0342465753')).toBe('0.0342465753')
  expect(parseRate('0.00000000001')).toBeNull()
  expect(parseRate('0')).toBeNull()
})
