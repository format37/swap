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
      'GET /api/v1/orders': (request) =>
        new URL(request.url).searchParams.get('scope') === 'mine'
          ? json(200, [
              order({
                id: 'mine',
                mine: true,
                author: NINO,
                give_currency: 'GEL',
                status: 'closed',
                available_until: null,
              }),
            ])
          : json(200, [order()]),
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
    expect(mine).toHaveTextContent('Закрыта · с 25 окт., без срока')
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
      'POST /api/v1/quote': () => json(200, { amount: '5136.99' }),
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
    fireEvent.click(screen.getByRole('button', { name: 'Карта' }))
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
    fireEvent.change(screen.getByRole('combobox', { name: /^Валюта/ }), {
      target: { value: 'GEL' },
    })
    expect(screen.getByRole('combobox', { name: /^Страна/ })).toHaveValue('GE')
    fireEvent.change(screen.getByRole('textbox', { name: 'Курс' }), { target: { value: '29,20' } })
    // The preview comes from the api, which does the arithmetic.
    await waitFor(() => {
      expect(document.body).toHaveTextContent('Отдав 150 000₽RUB, получите ≈ 5 136,99₾GEL')
    })
    expect(served).toContain('POST /api/v1/quote')
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
      payout_methods: ['card'],
      wants: [{ currency: 'GEL', country: 'GE' }],
      rate_spec: { v: 1, type: 'fixed', quotes: [{ base: 'GEL', quote: 'RUB', value: '29.20' }] },
      visible_to: null,
      note: 'вечером',
    })
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
    expect(screen.getByText('Карта')).toBeInTheDocument()
    expect(screen.getByText('Телефон (СБП)')).toBeInTheDocument()
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

  it('tells a stranger only that there is no such order', async () => {
    fakeApi({ [`GET /api/v1/orders/${ORDER_ID}`]: () => problem(404, 'order.not_found') })
    renderScreen(<OrderCard me={me} />, { route, path })
    expect(await screen.findByText('Заявка не найдена.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Повторить' })).toBeNull()
  })
})
