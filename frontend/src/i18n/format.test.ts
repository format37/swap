import { formatDate } from './format'

const ISO = '2026-10-25T12:00:00Z'

it('names the month in Russian and English', () => {
  expect(formatDate('ru', ISO, 'long')).toBe('25 октября')
  expect(formatDate('en', ISO, 'long')).toBe('25 October')
})

it('keeps Georgian dates numeric, whatever Intl knows of Georgian', () => {
  expect(formatDate('ka', ISO)).toBe('25.10')
  expect(formatDate('ka', ISO, 'long')).toBe('25.10.2026')
})
