import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Me } from '../api/client'
import type { Deal } from '../api/deals'
import type { Order, QuoteRequest, RateSpec } from '../api/orders'
import { backOverride } from '../back'
import { confirmAction, useMainButton, type MainAction } from '../telegram'
import { fakeApi, json, problem } from '../test/api'
import { deal } from '../test/deals'
import { renderScreen } from '../test/render'
import { Home } from './Home'
import { NewOrder } from './NewOrder'
import { OrderCard } from './OrderCard'

vi.mock('../telegram', () => ({
  useMainButton: vi.fn(),
  confirmAction: vi.fn(() => Promise.resolve(true)),
  hapticNotify: vi.fn(),
  hapticSelect: vi.fn(),
}))

function mainButton(): MainAction | null {
  return vi.mocked(useMainButton).mock.lastCall?.[0] ?? null
}

function press() {
  act(() => {
    mainButton()?.onClick()
  })
}

const ORDER_ID = 'd0000000-0000-4000-8000-000000000001'
const GIO = {
  id: 'a0000000-0000-4000-8000-000000000003',
  first_name: 'Gio',
  last_name: null,
  username: 'gio',
  photo_url: null,
  score: 0,
  deleted: false,
}
const MARKET: RateSpec = { v: 1, type: 'reference', source: 'coinbase' }

function fixed(base: string, quote: string, value: string): RateSpec {
  return { v: 1, type: 'fixed', quotes: [{ base, quote, value }] }
}
const ALEX = {
  id: 'a0000000-0000-4000-8000-000000000001',
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
  photo_url: null,
  score: 0,
  deleted: false,
}
const NINO = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
  photo_url: null,
  score: 0,
  deleted: false,
}

function order(changes: Partial<Order> = {}): Order {
  return {
    id: ORDER_ID,
    number: 17,
    author: ALEX,
    mine: false,
    give_currency: 'RUB',
    give_country: 'RU',
    amount_min: '10000.00',
    amount_max: '150000.00',
    amount_remaining: '150000.00',
    available_from: '2026-10-25',
    available_until: '2026-11-08',
    payout_methods: ['bank'],
    wants: [
      {
        currency: 'GEL',
        country: 'GE',
        rate_spec: fixed('GEL', 'RUB', '29.20'),
        receive_methods: ['cash', 'crypto'],
      },
      {
        currency: 'USD',
        country: 'GE',
        rate_spec: fixed('USD', 'RUB', '81.50'),
        receive_methods: ['bank'],
      },
    ],
    note: 'наличные у метро',
    status: 'open',
    repeat_day: null,
    created_at: '2026-10-22T10:00:00Z',
    visibility: null,
    ...changes,
  }
}

const me: Me = {
  id: ALEX.id,
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
  photo_url: null,
  score: 0,
  locale: 'ru',
  locale_chosen: false,
  telegram_locale: 'ru',
  tz: 'Asia/Tbilisi',
  notifications_off: false,
  muted_kinds: [],
  terms_accepted: true,
}

// One link, two people two handshakes away, none three away, and five farther.
const NETWORK = {
  rings: [
    { distance: 1, people: [NINO] },
    {
      distance: 2,
      people: [GIO, { ...GIO, id: 'a0000000-0000-4000-8000-000000000004', first_name: 'Ana' }],
    },
    { distance: 3, people: [] },
  ],
  farther: 5,
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('Home', () => {
  it('explains Swap in three steps while there is nothing at all', async () => {
    fakeApi({
      'GET /api/v1/links': () => json(200, { active: [], incoming: [], outgoing: [], invites: [] }),
      'GET /api/v1/orders': () => json(200, []),
      'GET /api/v1/deals': () => json(200, []),
    })
    renderScreen(<Home me={me} />)
    expect(await screen.findByText('Как это работает')).toBeInTheDocument()
    expect(screen.getByText('Пригласите знакомого')).toBeInTheDocument()
    expect(mainButton()?.text).toBe('Новая заявка')
  })

  it('shows link requests, my deals, orders open to me, then mine', async () => {
    fakeApi({
      'GET /api/v1/links': () =>
        json(200, {
          active: [
            {
              id: 'l1',
              person: ALEX,
              status: 'active',
              direction: 'outgoing',
              requested_at: '2026-10-20T10:00:00Z',
              accepted_at: '2026-10-21T10:00:00Z',
            },
          ],
          incoming: [
            {
              id: 'l2',
              person: NINO,
              status: 'pending',
              direction: 'incoming',
              requested_at: '2026-10-22T10:00:00Z',
              accepted_at: null,
            },
          ],
          outgoing: [],
          invites: [],
        }),
      'GET /api/v1/orders': (request) => {
        const scope = new URL(request.url).searchParams.get('scope')
        if (scope === 'mine')
          return json(200, [order({ id: 'mine', mine: true, author: NINO, give_currency: 'GEL' })])
        if (scope === 'history')
          return json(200, [
            order({
              id: 'closed',
              mine: true,
              author: NINO,
              give_currency: 'GEL',
              status: 'closed',
              available_until: null,
            }),
            order({ id: 'used-up', status: 'fulfilled', amount_remaining: '0.00' }),
          ])
        return json(200, [order()])
      },
      'GET /api/v1/deals': () => json(200, [deal({ role: 'acceptor' })]),
    })
    renderScreen(<Home me={me} />)
    const deals = (await screen.findByRole('heading', { name: 'Мои сделки' })).parentElement
    expect(deals).toHaveTextContent('Nino B · Новое предложение: примите его или отклоните')
    const requests = (await screen.findByRole('heading', { name: 'Запросы связи' })).parentElement
    expect(requests).toHaveTextContent('Nino B')
    const open = (await screen.findByRole('heading', { name: 'Открытые мне' })).parentElement
    // jest-dom reads a no-break space as a plain one.
    expect(open).toHaveTextContent('150 000₽RUB₾GEL$USD№ 17 · Alex · 25 окт. – 8 нояб.')
    const mine = screen.getByRole('heading', { name: 'Мои заявки' }).parentElement
    expect(mine).toHaveTextContent('Открыта')
    // Finished orders wait folded under one line, mine and those I dealt on (H4).
    const past = screen.getByRole('button', { name: 'Завершённые заявки (2)' })
    expect(past).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText(/Закрыта/)).toBeNull()
    fireEvent.click(past)
    expect(screen.getByText('№ 17 · Закрыта · с 25 окт., без срока')).toBeInTheDocument()
    expect(
      screen.getByText('№ 17 · Alex · Исполнена · 25 окт. – 8 нояб.').parentElement,
    ).toHaveTextContent('150 000₽RUB')
  })

  it('narrows the orders open to me to so many handshakes, folded until asked (J2)', async () => {
    const asked: (string | null)[] = []
    fakeApi({
      'GET /api/v1/links': () =>
        json(200, {
          active: [
            {
              id: 'l1',
              person: NINO,
              status: 'active',
              direction: 'outgoing',
              requested_at: '2026-10-20T10:00:00Z',
              accepted_at: '2026-10-21T10:00:00Z',
            },
          ],
          incoming: [],
          outgoing: [],
          invites: [],
        }),
      'GET /api/v1/orders': (request) => {
        const query = new URL(request.url).searchParams
        if (query.get('scope') === 'visible') asked.push(query.get('within'))
        return json(200, [])
      },
      'GET /api/v1/deals': () => json(200, []),
    })
    renderScreen(<Home me={me} />)
    const filter = await screen.findByRole('button', { name: 'Показаны: вся сеть' })
    expect(filter).toHaveAttribute('aria-expanded', 'false')
    expect(asked).toEqual([null])
    fireEvent.click(filter)
    fireEvent.click(screen.getByRole('button', { name: 'Мои связи' }))
    expect(await screen.findByRole('button', { name: 'Показаны: мои связи' })).toBeInTheDocument()
    await waitFor(() => {
      expect(asked).toContain('1')
    })
  })

  it('opens the wizard from the main button', async () => {
    fakeApi({
      'GET /api/v1/links': () => json(200, { active: [], incoming: [], outgoing: [], invites: [] }),
      'GET /api/v1/orders': () => json(200, []),
    })
    renderScreen(<Home me={me} />)
    press()
    expect(await screen.findByTestId('elsewhere')).toHaveTextContent('/orders/new')
  })
})

describe('the wizard', () => {
  it('walks two steps and publishes exactly what was typed', async () => {
    let published: unknown
    const { served } = fakeApi({
      'GET /api/v1/assets': () => json(200, ['RUB', 'GEL', 'USD']),
      'GET /api/v1/links': () =>
        json(200, {
          active: [
            {
              id: 'l1',
              person: NINO,
              status: 'active',
              direction: 'outgoing',
              requested_at: '2026-10-20T10:00:00Z',
              accepted_at: '2026-10-21T10:00:00Z',
            },
          ],
          incoming: [],
          outgoing: [],
          invites: [],
        }),
      'POST /api/v1/quote': () =>
        json(200, {
          amount: '5136.99',
          rate: { base: 'GEL', quote: 'RUB', value: '29.20', source: null, fetched_at: null },
        }),
      'GET /api/v1/me': () => json(200, me),
      'GET /api/v1/network': () => json(200, NETWORK),
      'POST /api/v1/orders': async (request) => {
        published = await request.json()
        return json(201, order({ mine: true }))
      },
    })
    renderScreen(<NewOrder />, { route: '/orders/new' })
    expect(screen.getByText('Шаг 1 из 2')).toBeInTheDocument()

    // Pressing on with nothing filled in says what is missing.
    press()
    expect(await screen.findByText('Выберите валюту и страну')).toBeInTheDocument()

    // Both sides on the first step, each under its own heading, with no titles inside (J1).
    expect(screen.getByRole('heading', { name: 'Отдаёте' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Получаете' })).toBeInTheDocument()
    await screen.findAllByRole('option', { name: '₽ RUB' })
    const [give, get] = screen.getAllByRole('combobox', { name: /^Валюта/ })
    const [giveCountry, getCountry] = screen.getAllByRole('combobox', { name: /^Страна/ })
    // Each list says which side it is for, in case its reader got distracted (F1).
    expect(within(give as HTMLElement).getByRole('option', { name: 'Отдаёте' })).toBeDisabled()
    expect(within(get as HTMLElement).getByRole('option', { name: 'Получаете' })).toBeDisabled()
    fireEvent.change(give as HTMLElement, { target: { value: 'RUB' } })
    // The currency's home is the first guess of the country.
    expect(giveCountry).toHaveValue('RU')
    fireEvent.change(screen.getByRole('textbox', { name: /^Сумма/ }), {
      target: { value: '150 000' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: /^Минимум за сделку/ }), {
      target: { value: '10000' },
    })
    const payOut = screen.getByRole('group', { name: 'Как вы можете отдать' })
    fireEvent.click(within(payOut).getByRole('button', { name: 'Банк' }))
    fireEvent.change(get as HTMLElement, { target: { value: 'GEL' } })
    expect(getCountry).toHaveValue('GE')
    // The author's own rate, fixed for this currency (QUESTIONS G2, J1).
    fireEvent.click(screen.getByRole('switch', { name: 'Зафиксировать курс' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Курс' }), { target: { value: '29,20' } })
    // What the sum comes to, from the api, which does the arithmetic (QUESTIONS L2).
    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /^Получите/ })).toHaveValue('5\u00a0136,99')
    })
    expect(served).toContain('POST /api/v1/quote')
    const payIn = screen.getByRole('group', { name: 'Как получать' })
    fireEvent.click(within(payIn).getByRole('button', { name: 'Наличные' }))
    press()

    // Step 2 opens with step 1 in a line.
    expect(await screen.findByText('Шаг 2 из 2')).toBeInTheDocument()
    expect(screen.getByText(/^Отдаёте/)).toHaveTextContent(
      'Отдаёте 150 000₽RUB · Россия → ₾GEL по 1 ₾GEL = 29,20 ₽RUB',
    )
    // BackButton steps back to step 1, keeping what was typed.
    act(() => {
      backOverride()?.()
    })
    expect(await screen.findByText('Шаг 1 из 2')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /^Сумма/ })).toHaveValue('150 000')
    press()

    await screen.findByText('Шаг 2 из 2')
    // A new order reaches links and their links, and says who that is (QUESTIONS J2).
    expect(screen.getByRole('slider', { name: 'Кому видно' })).toHaveAttribute(
      'aria-valuetext',
      'Вашим связям и их связям',
    )
    expect(
      await screen.findByText('Увидят: ваших связей — 1, дальше по цепочке — 2'),
    ).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'вечером' } })
    expect(mainButton()?.text).toBe('Опубликовать')
    press()

    expect(await screen.findByTestId('elsewhere')).toHaveTextContent(`/orders/${ORDER_ID}`)
    expect(published).toMatchObject({
      give_currency: 'RUB',
      give_country: 'RU',
      amount_max: '150000',
      amount_min: '10000',
      available_until: null,
      payout_methods: ['bank'],
      wants: [
        {
          currency: 'GEL',
          country: 'GE',
          rate_spec: fixed('GEL', 'RUB', '29.20'),
          receive_methods: ['cash'],
        },
      ],
      reach: 2,
      visible_to: null,
      note: 'вечером',
    })
  })

  it('reaches as far as the slider says, and at 0 only those chosen', async () => {
    let published: unknown
    fakeApi({
      'GET /api/v1/assets': () => json(200, ['RUB', 'GEL']),
      'GET /api/v1/links': () =>
        json(200, {
          active: [
            {
              id: 'l1',
              person: NINO,
              status: 'active',
              direction: 'outgoing',
              requested_at: '2026-10-20T10:00:00Z',
              accepted_at: '2026-10-21T10:00:00Z',
            },
          ],
          incoming: [],
          outgoing: [],
          invites: [],
        }),
      'GET /api/v1/rates/market': () => problem(503, 'rate.unavailable'),
      'GET /api/v1/me': () => json(200, me),
      'GET /api/v1/network': () => json(200, NETWORK),
      'POST /api/v1/orders': async (request) => {
        published = await request.json()
        return json(201, order({ mine: true }))
      },
    })
    renderScreen(<NewOrder />, { route: '/orders/new' })
    await screen.findAllByRole('option', { name: '₽ RUB' })
    const [give, get] = screen.getAllByRole('combobox', { name: /^Валюта/ })
    fireEvent.change(give as HTMLElement, { target: { value: 'RUB' } })
    fireEvent.change(screen.getByRole('textbox', { name: /^Сумма/ }), {
      target: { value: '1000' },
    })
    fireEvent.click(
      within(screen.getByRole('group', { name: 'Как вы можете отдать' })).getByRole('button', {
        name: 'Банк',
      }),
    )
    fireEvent.change(get as HTMLElement, { target: { value: 'GEL' } })
    fireEvent.click(
      within(screen.getByRole('group', { name: 'Как получать' })).getByRole('button', {
        name: 'Наличные',
      }),
    )
    press()
    await screen.findByText('Шаг 2 из 2')
    // The whole network: the rings' farthest count joins the line.
    fireEvent.click(screen.getByRole('button', { name: 'Вся сеть' }))
    expect(
      await screen.findByText('Увидят: ваших связей — 1, дальше по цепочке — 7'),
    ).toBeInTheDocument()
    // «Только выбранным» lists the author's links, and needs one of them.
    fireEvent.change(screen.getByRole('slider', { name: 'Кому видно' }), { target: { value: '0' } })
    expect(screen.getByText('Увидят только выбранные: 0')).toBeInTheDocument()
    press()
    expect(await screen.findByText('Выберите хотя бы одну связь')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: /Nino B/ }))
    press()
    await screen.findByTestId('elsewhere')
    expect(published).toMatchObject({ reach: 0, visible_to: [NINO.id] })
  })

  it('fixes the rate per currency, and says so in the digest', async () => {
    let published: unknown
    fakeApi({
      'GET /api/v1/assets': () => json(200, ['RUB', 'GEL', 'USD']),
      'GET /api/v1/links': () => json(200, { active: [], incoming: [], outgoing: [], invites: [] }),
      'GET /api/v1/rates/market': () => problem(503, 'rate.unavailable'),
      'POST /api/v1/quote': () =>
        json(200, {
          amount: '1840.49',
          rate: { base: 'USD', quote: 'RUB', value: '81.50', source: null, fetched_at: null },
        }),
      'POST /api/v1/orders': async (request) => {
        published = await request.json()
        return json(201, order({ mine: true }))
      },
    })
    renderScreen(<NewOrder />, { route: '/orders/new' })
    await screen.findAllByRole('option', { name: '₽ RUB' })
    const [give, first] = screen.getAllByRole('combobox', { name: /^Валюта/ })
    fireEvent.change(give as HTMLElement, { target: { value: 'RUB' } })
    fireEvent.change(screen.getByRole('textbox', { name: /^Сумма/ }), {
      target: { value: '150000' },
    })
    fireEvent.click(
      within(screen.getByRole('group', { name: 'Как вы можете отдать' })).getByRole('button', {
        name: 'Банк',
      }),
    )
    fireEvent.change(first as HTMLElement, { target: { value: 'GEL' } })
    // GEL in cash or by bank...
    const gelWays = screen.getByRole('group', { name: 'Как получать' })
    fireEvent.click(within(gelWays).getByRole('button', { name: 'Наличные' }))
    fireEvent.click(within(gelWays).getByRole('button', { name: 'Банк' }))
    fireEvent.click(screen.getByRole('button', { name: 'Ещё валюта' }))
    const second = screen.getAllByRole('combobox', { name: /^Валюта/ })[2] as HTMLElement
    fireEvent.change(second, { target: { value: 'USD' } })
    fireEvent.change(screen.getAllByRole('combobox', { name: /^Страна/ })[2] as HTMLElement, {
      target: { value: 'GE' },
    })
    // ...and USD, which starts with GEL's ways, by bank alone (QUESTIONS L1).
    const usdWays = screen.getAllByRole('group', { name: 'Как получать' })[1] as HTMLElement
    expect(within(usdWays).getByRole('button', { name: 'Наличные' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    fireEvent.click(within(usdWays).getByRole('button', { name: 'Наличные' }))
    // GEL follows the market; USD is fixed, so only USD's rate asks to be typed.
    const switches = screen.getAllByRole('switch', { name: 'Зафиксировать курс' })
    fireEvent.click(switches[1] as HTMLElement)
    expect(switches[0]).toHaveAttribute('aria-checked', 'false')
    press()
    expect(await screen.findByText('Введите курс, например 29,20')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Курс' }), { target: { value: '81,50' } })
    press()

    await screen.findByText('Шаг 2 из 2')
    expect(screen.getByText(/^Отдаёте/)).toHaveTextContent(
      'Отдаёте 150 000₽RUB · Россия → ₾GEL по рынку или $USD по 1 $USD = 81,50 ₽RUB',
    )
    press()
    await screen.findByTestId('elsewhere')
    expect(published).toMatchObject({
      wants: [
        { currency: 'GEL', country: 'GE', rate_spec: MARKET, receive_methods: ['cash', 'bank'] },
        {
          currency: 'USD',
          country: 'GE',
          rate_spec: fixed('USD', 'RUB', '81.50'),
          receive_methods: ['bank'],
        },
      ],
    })
  })
})

describe('what one gets (L2)', () => {
  it('follows in English too, whichever currency was typed and added first (M2)', async () => {
    // The owner's steps: the sum, GEL typed, then USD added, then USD typed.
    const answers: Record<string, string> = {
      'want 100 GEL': '2920.00',
      'give 2920 USD': '35.83',
      'want 50 USD': '4075.00',
      'give 4075 GEL': '139.55',
    }
    fakeApi({
      'GET /api/v1/assets': () => json(200, ['RUB', 'GEL', 'USD']),
      'GET /api/v1/links': () => json(200, { active: [], incoming: [], outgoing: [], invites: [] }),
      'GET /api/v1/rates/market': () => problem(503, 'rate.unavailable'),
      'POST /api/v1/quote': async (request) => {
        const body = (await request.json()) as QuoteRequest
        const amount = answers[`${body.side} ${body.amount} ${body.want_currency}`] ?? '0.00'
        return json(200, {
          amount,
          rate: {
            base: body.want_currency,
            quote: 'RUB',
            value: '1',
            source: null,
            fetched_at: null,
          },
        })
      },
    })
    renderScreen(<NewOrder />, { route: '/orders/new', locale: 'en' })
    await screen.findAllByRole('option', { name: '₽ RUB' })
    const [give, first] = screen.getAllByRole('combobox', { name: /^Currency/ })
    fireEvent.change(give as HTMLElement, { target: { value: 'RUB' } })
    const sum = screen.getByRole('textbox', { name: /^Amount/ })
    fireEvent.change(sum, { target: { value: '150000' } })
    fireEvent.change(first as HTMLElement, { target: { value: 'GEL' } })
    fireEvent.click(screen.getByRole('switch', { name: 'Fix the rate' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Rate' }), { target: { value: '29.20' } })
    const gets = () => screen.getAllByRole('textbox', { name: /^You get/ })

    fireEvent.change(gets()[0] as HTMLElement, { target: { value: '100' } })
    await waitFor(() => {
      expect(sum).toHaveValue('2,920')
    })
    // USD, added after GEL was typed, follows the sum as written in English.
    fireEvent.click(screen.getByRole('button', { name: 'Another currency' }))
    fireEvent.change(screen.getAllByRole('combobox', { name: /^Currency/ })[2] as HTMLElement, {
      target: { value: 'USD' },
    })
    fireEvent.change(screen.getAllByRole('combobox', { name: /^Country/ })[2] as HTMLElement, {
      target: { value: 'GE' },
    })
    fireEvent.click(screen.getAllByRole('switch', { name: 'Fix the rate' })[1] as HTMLElement)
    fireEvent.change(screen.getAllByRole('textbox', { name: 'Rate' })[1] as HTMLElement, {
      target: { value: '81.50' },
    })
    await waitFor(() => {
      expect(gets()[1]).toHaveValue('35.83')
    })
    // Typing USD now: GEL follows the new sum instead of emptying.
    fireEvent.change(gets()[1] as HTMLElement, { target: { value: '50' } })
    await waitFor(() => {
      expect(sum).toHaveValue('4,075')
    })
    await waitFor(() => {
      expect(gets()[0]).toHaveValue('139.55')
    })
  })

  it('can be typed, and the sum and the other currencies follow it', async () => {
    const asked: QuoteRequest[] = []
    // What the api answers, «1 GEL = 29,20 RUB» and «1 USD = 81,50 RUB»: no arithmetic here.
    const answers: Record<string, string> = {
      'want 100 GEL': '2920.00',
      'give 2920 USD': '35.83',
      'give 5840 GEL': '200.00',
      'give 5840 USD': '71.66',
    }
    fakeApi({
      'GET /api/v1/assets': () => json(200, ['RUB', 'GEL', 'USD']),
      'GET /api/v1/links': () => json(200, { active: [], incoming: [], outgoing: [], invites: [] }),
      'GET /api/v1/rates/market': () => problem(503, 'rate.unavailable'),
      'POST /api/v1/quote': async (request) => {
        const body = (await request.json()) as QuoteRequest
        asked.push(body)
        const amount = answers[`${body.side} ${body.amount} ${body.want_currency}`] ?? '0.00'
        return json(200, {
          amount,
          rate: {
            base: body.want_currency,
            quote: 'RUB',
            value: '1',
            source: null,
            fetched_at: null,
          },
        })
      },
    })
    renderScreen(<NewOrder />, { route: '/orders/new' })
    await screen.findAllByRole('option', { name: '₽ RUB' })
    const [give, first] = screen.getAllByRole('combobox', { name: /^Валюта/ })
    fireEvent.change(give as HTMLElement, { target: { value: 'RUB' } })
    fireEvent.change(first as HTMLElement, { target: { value: 'GEL' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ещё валюта' }))
    fireEvent.change(screen.getAllByRole('combobox', { name: /^Валюта/ })[2] as HTMLElement, {
      target: { value: 'USD' },
    })
    fireEvent.change(screen.getAllByRole('combobox', { name: /^Страна/ })[2] as HTMLElement, {
      target: { value: 'GE' },
    })
    for (const [index, rate] of ['29,20', '81,50'].entries()) {
      fireEvent.click(
        screen.getAllByRole('switch', { name: 'Зафиксировать курс' })[index] as HTMLElement,
      )
      fireEvent.change(screen.getAllByRole('textbox', { name: 'Курс' })[index] as HTMLElement, {
        target: { value: rate },
      })
    }
    const gets = () => screen.getAllByRole('textbox', { name: /^Получите/ })
    const sum = screen.getByRole('textbox', { name: /^Сумма/ })

    // 100 GEL typed: the api says what to give for it, and USD follows the new sum.
    fireEvent.change(gets()[0] as HTMLElement, { target: { value: '100' } })
    await waitFor(() => {
      expect(sum).toHaveValue('2\u00a0920')
    })
    expect(asked).toContainEqual(
      expect.objectContaining({ amount: '100', want_currency: 'GEL', side: 'want' }),
    )
    await waitFor(() => {
      expect(gets()[1]).toHaveValue('35,83')
    })
    // What was typed stays as it was typed.
    expect(gets()[0]).toHaveValue('100')

    // The sum typed leads again, and both currencies follow it.
    fireEvent.change(sum, { target: { value: '5840' } })
    await waitFor(() => {
      expect(gets()[0]).toHaveValue('200')
    })
    await waitFor(() => {
      expect(gets()[1]).toHaveValue('71,66')
    })
  })
})

describe('the wizard’s rate', () => {
  it('is the market’s until the author types one, and can be had back', async () => {
    const at = new Date()
    at.setHours(10, 30, 0, 0)
    fakeApi({
      'GET /api/v1/assets': () => json(200, ['RUB', 'GEL']),
      'GET /api/v1/rates/market': (request) => {
        const query = new URL(request.url).searchParams
        const base = query.get('base')
        return json(200, {
          base,
          quote: query.get('quote'),
          value: base === 'GEL' ? '31.39' : '0.03185',
          source: 'coinbase',
          fetched_at: at.toISOString(),
        })
      },
      'POST /api/v1/quote': () =>
        json(200, {
          amount: '4778.59',
          rate: { base: 'GEL', quote: 'RUB', value: '29.20', source: null, fetched_at: null },
        }),
    })
    renderScreen(<NewOrder />, { route: '/orders/new' })
    await screen.findAllByRole('option', { name: '₽ RUB' })
    const [give, get] = screen.getAllByRole('combobox', { name: /^Валюта/ })
    fireEvent.change(give as HTMLElement, { target: { value: 'RUB' } })
    fireEvent.change(screen.getByRole('textbox', { name: /^Сумма/ }), {
      target: { value: '150000' },
    })
    fireEvent.change(get as HTMLElement, { target: { value: 'GEL' } })
    // Followed, the market's rate only shows (QUESTIONS G2).
    await waitFor(() => {
      expect(document.body).toHaveTextContent('Курс1 ₾GEL = 31,39 ₽RUB')
    })
    expect(screen.queryByRole('textbox', { name: 'Курс' })).toBeNull()
    fireEvent.click(screen.getByRole('switch', { name: 'Зафиксировать курс' }))

    // Fixed, it starts at the market's, with where it comes from and when (F5, §11).
    const rate = screen.getByRole('textbox', { name: 'Курс' })
    await waitFor(() => {
      expect(rate).toHaveValue('31,39')
    })
    // Only where it comes from and when, while the rate is the market's own.
    expect(screen.getByText(/Курс Coinbase/)).toHaveTextContent(/^Курс Coinbase, 10:30$/)
    // The other way round, it is the market's again.
    fireEvent.click(screen.getByRole('button', { name: 'Поменять направление курса' }))
    await waitFor(() => {
      expect(rate).toHaveValue('0,03185')
    })
    // What the author types stays, even emptied, until they ask for the market's back.
    fireEvent.change(rate, { target: { value: '' } })
    expect(rate).toHaveValue('')
    fireEvent.change(rate, { target: { value: '0,032' } })
    expect(rate).toHaveValue('0,032')
    expect(screen.getByText(/Курс Coinbase/)).toHaveTextContent(
      'Курс Coinbase, 10:30: 1 ₽RUB = 0,03185 ₾GEL',
    )
    fireEvent.click(screen.getByText(/Курс Coinbase/))
    expect(rate).toHaveValue('0,03185')
  })
})

describe('the order card', () => {
  const route = `/orders/${ORDER_ID}`
  const path = '/orders/:id'

  it('shows what remains, for what, how and when', async () => {
    fakeApi({ [`GET /api/v1/orders/${ORDER_ID}`]: () => json(200, order()) })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText(/Осталось/)).toHaveTextContent('Осталось: 150 000₽RUB')
    expect(screen.getByText(/за одну сделку/)).toHaveTextContent('От 10 000₽RUB за одну сделку')
    const wants = screen.getByRole('heading', { name: 'Хочет взамен' }).parentElement
    expect(within(wants as HTMLElement).getAllByText(/Курс: 1/)[0]).toHaveTextContent(
      'Курс: 1 ₾GEL = 29,20 ₽RUB',
    )
    // How the author takes each currency sits with it (F2, L1): GEL in cash or crypto, USD
    // by bank; and how they pay out, by bank too, with what they give.
    expect(within(wants as HTMLElement).getByText('Наличные')).toBeInTheDocument()
    expect(within(wants as HTMLElement).getByText('Крипто')).toBeInTheDocument()
    expect(within(wants as HTMLElement).getByText('Банк')).toBeInTheDocument()
    expect(screen.getAllByText('Банк')).toHaveLength(2)
    expect(screen.getByText('наличные у метро')).toBeInTheDocument()
    // Someone else's order: no list of who sees it, and nothing to close.
    expect(screen.queryByText(/Видно/)).toBeNull()
    expect(screen.queryByRole('button', { name: 'Закрыть заявку' })).toBeNull()
  })

  it('says nothing of a minimum of 0, and that there is no last day', async () => {
    fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () =>
        json(200, order({ amount_min: '0.00', available_until: null })),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText('с 25 окт., без срока')).toBeInTheDocument()
    expect(screen.getByText('Россия')).toBeInTheDocument()
    expect(screen.queryByText(/за одну сделку/)).toBeNull()
  })

  it('lets its author see who sees it, and close it once that is confirmed', async () => {
    const { served } = fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () =>
        json(200, order({ mine: true, visibility: { reach: 0, people: [NINO] } })),
      [`POST /api/v1/orders/${ORDER_ID}/close`]: () =>
        json(200, order({ mine: true, status: 'closed' })),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText('Видно только: Nino B')).toBeInTheDocument()
    vi.mocked(confirmAction).mockResolvedValueOnce(false)
    fireEvent.click(screen.getByRole('button', { name: 'Закрыть заявку' }))
    await waitFor(() => {
      expect(confirmAction).toHaveBeenCalledTimes(1)
    })
    expect(served).not.toContain(`POST /api/v1/orders/${ORDER_ID}/close`)
    fireEvent.click(screen.getByRole('button', { name: 'Закрыть заявку' }))
    await waitFor(() => {
      expect(served).toContain(`POST /api/v1/orders/${ORDER_ID}/close`)
    })
  })

  it('lets its author reopen a closed order, or delete it once that is confirmed', async () => {
    const { served } = fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () => json(200, order({ mine: true, status: 'closed' })),
      'GET /api/v1/deals': () => json(200, [deal({ status: 'settled', role: 'acceptor' })]),
      [`POST /api/v1/orders/${ORDER_ID}/reopen`]: () => json(200, order({ mine: true })),
      [`DELETE /api/v1/orders/${ORDER_ID}`]: () => new Response(null, { status: 204 }),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    fireEvent.click(await screen.findByRole('button', { name: 'Открыть снова' }))
    await waitFor(() => {
      expect(served).toContain(`POST /api/v1/orders/${ORDER_ID}/reopen`)
    })
    vi.mocked(confirmAction).mockResolvedValueOnce(false)
    fireEvent.click(screen.getByRole('button', { name: 'Удалить заявку' }))
    await waitFor(() => {
      expect(confirmAction).toHaveBeenCalledWith(
        'Удалить заявку и все сделки по ней у себя? У других участников они останутся. Вернуть их нельзя.',
        'Удалить заявку',
        { destructive: true },
      )
    })
    expect(served).not.toContain(`DELETE /api/v1/orders/${ORDER_ID}`)
    fireEvent.click(screen.getByRole('button', { name: 'Удалить заявку' }))
    await waitFor(() => {
      expect(served).toContain(`DELETE /api/v1/orders/${ORDER_ID}`)
    })
  })

  it.each<[Order['status'], string[]]>([
    ['open', ['Закрыть заявку']],
    ['fulfilled', ['Удалить заявку']],
    ['expired', ['Удалить заявку']],
  ])('offers its author of a %s order only %j', async (status, actions) => {
    fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () => json(200, order({ mine: true, status })),
      'GET /api/v1/deals': () => json(200, []),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    await screen.findByText(/Осталось/)
    await screen.findAllByRole('button')
    const offered = ['Закрыть заявку', 'Открыть снова', 'Удалить заявку'].filter((name) =>
      screen.queryByRole('button', { name }),
    )
    expect(offered).toEqual(actions)
  })

  it('offers its author no deletion while a deal on it runs (J3)', async () => {
    fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () =>
        json(200, order({ mine: true, status: 'fulfilled' })),
      'GET /api/v1/deals': () => json(200, [deal({ status: 'accepted', role: 'acceptor' })]),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    await screen.findByText(/Сделки по заявке/i)
    expect(screen.queryByRole('button', { name: 'Удалить заявку' })).toBeNull()
  })

  it('offers whoever dealt on it to delete their deals on it, once all are over (L4)', async () => {
    const { served } = fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () => json(200, order({ status: 'fulfilled' })),
      'GET /api/v1/deals': () => json(200, [deal({ status: 'settled' })]),
      [`DELETE /api/v1/orders/${ORDER_ID}`]: () => new Response(null, { status: 204 }),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    fireEvent.click(await screen.findByRole('button', { name: 'Удалить у себя' }))
    await waitFor(() => {
      expect(served).toContain(`DELETE /api/v1/orders/${ORDER_ID}`)
    })
    expect(confirmAction).toHaveBeenCalledWith(
      'Удалить у себя ваши сделки по этой заявке? У автора они останутся. Вернуть их нельзя.',
      'Удалить у себя',
      { destructive: true },
    )
  })

  it.each<[string, Deal[]]>([
    [
      'while a deal of theirs runs',
      [
        deal({ status: 'settled' }),
        deal({ id: 'f0000000-0000-4000-8000-000000000002', status: 'accepted' }),
      ],
    ],
    ['to someone with no deal on it', []],
  ])('offers no deletion of someone else’s order %s', async (_, theirs) => {
    fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () => json(200, order({ status: 'fulfilled' })),
      'GET /api/v1/deals': () => json(200, theirs),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    await screen.findByText(/Осталось/)
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Удалить у себя' })).toBeNull()
    })
  })

  it('says why a closed order past its last day can’t reopen', async () => {
    fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () => json(200, order({ mine: true, status: 'closed' })),
      [`POST /api/v1/orders/${ORDER_ID}/reopen`]: () => problem(409, 'order.window_past'),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    fireEvent.click(await screen.findByRole('button', { name: 'Открыть снова' }))
    expect(
      await screen.findByText('Последний день заявки прошёл, открыть её снова нельзя.'),
    ).toBeInTheDocument()
  })

  it('shows the market rate of the moment for an order that follows it', async () => {
    const at = new Date()
    at.setHours(12, 0, 0, 0)
    const { served } = fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () =>
        json(
          200,
          order({
            wants: [
              { currency: 'GEL', country: 'GE', rate_spec: MARKET, receive_methods: ['cash'] },
            ],
          }),
        ),
      'GET /api/v1/rates/market': () =>
        json(200, {
          base: 'GEL',
          quote: 'RUB',
          value: '31.39',
          source: 'coinbase',
          fetched_at: at.toISOString(),
        }),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    // Whoever opens it gets the rate of this moment (QUESTIONS G2).
    expect(await screen.findByText(/Coinbase, 12:00/)).toBeInTheDocument()
    expect(screen.getByText(/Курс по рынку/).parentElement).toHaveTextContent(
      'Курс по рынку: 1 ₾GEL = 31,39 ₽RUB· Coinbase, 12:00',
    )
    expect(served).toContain('GET /api/v1/rates/market')
  })

  it('shows how its viewer reaches its author, their own link first (J2)', async () => {
    fakeApi({ [`GET /api/v1/orders/${ORDER_ID}`]: () => json(200, order({ chain: [NINO, GIO] })) })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText('Через Nino B → Gio')).toBeInTheDocument()
  })

  it.each<[number | null, string]>([
    [1, 'Видно вашим связям'],
    [2, 'Видно вашим связям и их связям'],
    [3, 'Видно на три рукопожатия от вас'],
    [null, 'Видно всей вашей сети'],
  ])('tells its author how far it reaches, at %s', async (reach, text) => {
    fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () =>
        json(200, order({ mine: true, visibility: { reach, people: [] } })),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText(text)).toBeInTheDocument()
  })

  it('says it repeats, and lets its author stop it once that is confirmed (K7)', async () => {
    const { served } = fakeApi({
      [`GET /api/v1/orders/${ORDER_ID}`]: () =>
        json(200, order({ mine: true, repeat_day: 5, visibility: { reach: 2, people: [] } })),
      'GET /api/v1/deals': () => json(200, []),
      [`POST /api/v1/orders/${ORDER_ID}/stop-repeating`]: () =>
        json(200, order({ mine: true, repeat_day: null })),
    })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText('Повторяется каждый месяц, 5-го числа')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Больше не повторять' }))
    await waitFor(() => {
      expect(served).toContain(`POST /api/v1/orders/${ORDER_ID}/stop-repeating`)
    })
  })

  it('tells a stranger only that there is no such order', async () => {
    fakeApi({ [`GET /api/v1/orders/${ORDER_ID}`]: () => problem(404, 'order.not_found') })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText('Заявка не найдена.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Повторить' })).toBeNull()
  })
})
