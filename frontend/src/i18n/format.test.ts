import { formatDate, formatDates } from './format'

const ISO = '2026-10-25T12:00:00Z'

it('names the month in Russian and English', () => {
  expect(formatDate('ru', ISO, 'long')).toBe('25 октября')
  expect(formatDate('en', ISO, 'long')).toBe('25 October')
})

it('keeps Georgian dates numeric, whatever Intl knows of Georgian', () => {
  expect(formatDate('ka', ISO)).toBe('25.10')
  expect(formatDate('ka', ISO, 'long')).toBe('25.10.2026')
})

it('reads a calendar date as that day wherever the reader is', () => {
  expect(formatDate('ru', '2026-10-25')).toBe('25 окт.')
  expect(formatDates('ka', '2026-10-25', '2026-11-08')).toBe('25.10 – 08.11')
})
