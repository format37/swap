import { expect, it } from 'vitest'

import type { Order } from '../api/orders'
import { translate } from '../i18n/translate'
import { shareText } from './share'

const ORDER: Order = {
  id: 'd0000000-0000-4000-8000-000000000001',
  number: 17,
  author: {
    id: 'a0000000-0000-4000-8000-000000000001',
    first_name: 'Alex',
    last_name: null,
    username: 'format37',
    photo_url: null,
    score: 0,
    deleted: false,
  },
  mine: true,
  give_currency: 'RUB',
  give_country: 'RU',
  amount_min: '0.00',
  amount_max: '150000.00',
  amount_remaining: '150000.00',
  available_from: '2026-10-25',
  available_until: null,
  payout_methods: ['bank'],
  wants: [
    {
      currency: 'USD',
      country: 'GE',
      rate_spec: { v: 1, type: 'fixed', quotes: [{ base: 'USD', quote: 'RUB', value: '81.50' }] },
      receive_methods: ['bank'],
      amount: '1840.49',
    },
  ],
  note: null,
  status: 'open',
  repeat_day: null,
  created_at: '2026-10-22T10:00:00Z',
}

it('writes an order the way its language writes numbers (O1)', () => {
  const t = (locale: 'en' | 'ka') => ({
    locale,
    t: (key: Parameters<typeof translate>[1], values?: Parameters<typeof translate>[2]) =>
      translate(locale, key, values),
  })
  expect(shareText(t('en'), ORDER)).toBe(
    [
      'I give 150,000 ₽ RUB · Russia',
      '→ 1,840.49 $ USD at 1 USD = 81.50 RUB',
      'Offer No. 17 in Swap',
    ].join('\n'),
  )
  expect(shareText(t('ka'), ORDER).split('\n').at(-1)).toBe('განცხადება № 17 Swap-ში')
})
