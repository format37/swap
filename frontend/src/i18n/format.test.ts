import { formatDate, formatDates, formatTime } from './format'

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

it('gives a rate’s time alone today, and with its date on another day', () => {
  const now = new Date(2026, 9, 22, 18, 0)
  expect(formatTime('ru', new Date(2026, 9, 22, 7, 5).toISOString(), now)).toBe('07:05')
  expect(formatTime('ka', new Date(2026, 9, 21, 7, 5).toISOString(), now)).toBe('21.10, 07:05')
})
