import { formatAmount, formatRate, parseAmount, parseRate } from './format'

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
  ['0', null],
  ['0,00', null],
  ['', null],
  ['12.345', null],
  ['-5', null],
  ['1e3', null],
  ['abc', null],
])('reads the amount %j as %j', (typed, expected) => {
  expect(parseAmount(typed)).toBe(expected)
})

it('reads a rate with up to ten decimals', () => {
  expect(parseRate('29,20')).toBe('29.20')
  expect(parseRate('0.0342465753')).toBe('0.0342465753')
  expect(parseRate('0.00000000001')).toBeNull()
  expect(parseRate('0')).toBeNull()
})
