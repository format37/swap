import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Me } from '../api/client'
import type { Order } from '../api/orders'
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
const ALEX = {
  id: 'a0000000-0000-4000-8000-000000000001',
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
}
const NINO = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
}

function order(changes: Partial<Order> = {}): Order {
  return {
    id: ORDER_ID,
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
    receive_methods: ['cash', 'crypto'],
    wants: [
      { currency: 'GEL', country: 'GE' },
      { currency: 'USD', country: 'GE' },
    ],
    rate_spec: {
      v: 1,
      type: 'fixed',
      quotes: [
        { base: 'GEL', quote: 'RUB', value: '29.20' },
        { base: 'USD', quote: 'RUB', value: '81.50' },
      ],
    },
    note: 'наличные у метро',
    status: 'open',
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
  locale: 'ru',
  locale_chosen: false,
  tz: 'Asia/Tbilisi',
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
            order({ id: 'used-up', status: 'fulfilled' }),
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
    expect(open).toHaveTextContent('150 000₽RUB₾GEL$USDAlex · 25 окт. – 8 нояб.')
    const mine = screen.getByRole('heading', { name: 'Мои заявки' }).parentElement
    expect(mine).toHaveTextContent('Открыта')
    // Finished orders wait folded under one line, mine and those I dealt on (H4).
    const past = screen.getByRole('button', { name: 'Завершённые заявки (2)' })
    expect(past).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText(/Закрыта/)).toBeNull()
    fireEvent.click(past)
    expect(screen.getByText('Закрыта · с 25 окт., без срока')).toBeInTheDocument()
    expect(screen.getByText('Alex · Исполнена · 25 окт. – 8 нояб.')).toBeInTheDocument()
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
  it('walks three steps and publishes exactly what was typed', async () => {
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
      'POST /api/v1/orders': async (request) => {
        published = await request.json()
        return json(201, order({ mine: true }))
      },
    })
    renderScreen(<NewOrder />, { route: '/orders/new' })
    expect(screen.getByText('Шаг 1 из 3')).toBeInTheDocument()

    // Pressing on with nothing filled in says what is missing.
    press()
    expect(await screen.findByText('Выберите валюту и страну')).toBeInTheDocument()

    await screen.findByRole('option', { name: '₽ RUB' })
    // The list says which side it is for, in case its reader got distracted (F1).
    expect(screen.getByRole('option', { name: 'Отдаёте' })).toBeDisabled()
    fireEvent.change(screen.getByRole('combobox', { name: /^Валюта/ }), {
      target: { value: 'RUB' },
    })
    // The currency's home is the first guess of the country.
    expect(screen.getByRole('combobox', { name: /^Страна/ })).toHaveValue('RU')
    fireEvent.change(screen.getByRole('textbox', { name: /^Всего/ }), {
      target: { value: '150 000' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: /^Минимум за сделку/ }), {
      target: { value: '10000' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Банк' }))
    press()
    expect(await screen.findByText('Шаг 2 из 3')).toBeInTheDocument()

    // BackButton steps back through the wizard, keeping what was typed.
    act(() => {
      backOverride()?.()
    })
    expect(await screen.findByText('Шаг 1 из 3')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /^Всего/ })).toHaveValue('150 000')
    press()

    await screen.findByText('Шаг 2 из 3')
    expect(screen.getByRole('option', { name: 'Получаете' })).toBeDisabled()
    fireEvent.change(screen.getByRole('combobox', { name: /^Валюта/ }), {
      target: { value: 'GEL' },
    })
    expect(screen.getByRole('combobox', { name: /^Страна/ })).toHaveValue('GE')
    // The author's own rate, fixed (QUESTIONS G2).
    fireEvent.click(screen.getByRole('switch', { name: 'Зафиксировать курс' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Курс' }), { target: { value: '29,20' } })
    // The preview comes from the api, which does the arithmetic.
    await waitFor(() => {
      expect(document.body).toHaveTextContent('Отдав 150 000₽RUB, получите ≈ 5 136,99₾GEL')
    })
    expect(served).toContain('POST /api/v1/quote')
    fireEvent.click(screen.getByRole('button', { name: 'Наличные' }))
    press()

    await screen.findByText('Шаг 3 из 3')
    expect(screen.getByRole('radio', { name: 'Всем моим связям' })).toHaveAttribute(
      'aria-checked',
      'true',
    )
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
      receive_methods: ['cash'],
      wants: [{ currency: 'GEL', country: 'GE' }],
      rate_spec: { v: 1, type: 'fixed', quotes: [{ base: 'GEL', quote: 'RUB', value: '29.20' }] },
      visible_to: null,
      note: 'вечером',
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
    await screen.findByRole('option', { name: '₽ RUB' })
    fireEvent.change(screen.getByRole('combobox', { name: /^Валюта/ }), {
      target: { value: 'RUB' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: /^Всего/ }), {
      target: { value: '150000' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Банк' }))
    press()
    await screen.findByText('Шаг 2 из 3')
    fireEvent.change(screen.getByRole('combobox', { name: /^Валюта/ }), {
      target: { value: 'GEL' },
    })
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
    expect(screen.getByText('Банк')).toBeInTheDocument()
    // How the author is paid sits with what they want (F2).
    expect(within(wants as HTMLElement).getByText('Наличные')).toBeInTheDocument()
    expect(within(wants as HTMLElement).getByText('Крипто')).toBeInTheDocument()
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
        json(200, order({ mine: true, visibility: { all_links: false, people: [NINO] } })),
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
        'Удалить заявку? Она пропадёт и у вас. Сделки по ней продолжатся.',
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
    fakeApi({ [`GET /api/v1/orders/${ORDER_ID}`]: () => json(200, order({ mine: true, status })) })
    renderScreen(<OrderCard me={me} />, { route, path })
    await screen.findByText(/Осталось/)
    const offered = ['Закрыть заявку', 'Открыть снова', 'Удалить заявку'].filter((name) =>
      screen.queryByRole('button', { name }),
    )
    expect(offered).toEqual(actions)
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
            rate_spec: { v: 1, type: 'reference', source: 'coinbase' },
            wants: [{ currency: 'GEL', country: 'GE' }],
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

  it('tells a stranger only that there is no such order', async () => {
    fakeApi({ [`GET /api/v1/orders/${ORDER_ID}`]: () => problem(404, 'order.not_found') })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText('Заявка не найдена.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Повторить' })).toBeNull()
  })
})
