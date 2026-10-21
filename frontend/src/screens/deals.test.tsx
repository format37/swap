import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Me } from '../api/client'
import type { Order } from '../api/orders'
import { confirmAction, useMainButton, type MainAction } from '../telegram'
import { ALEX, deal, DEAL_ID, NINO } from '../test/deals'
import { fakeApi, json, problem } from '../test/api'
import { renderScreen } from '../test/render'
import { DealCard } from './DealCard'
import { ProposeDeal } from './ProposeDeal'

vi.mock('../telegram', () => ({
  useMainButton: vi.fn(),
  confirmAction: vi.fn(() => Promise.resolve(true)),
  copyText: vi.fn(() => Promise.resolve(true)),
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

function meOf(person: Pick<Me, 'id' | 'first_name' | 'last_name' | 'username'>): Me {
  return { ...person, locale: 'ru', locale_chosen: false, tz: 'Asia/Tbilisi' }
}

const route = `/deals/${DEAL_ID}`
const path = '/deals/:id'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('the deal card', () => {
  it('says what to do next and shows both legs', async () => {
    fakeApi({
      [`GET /api/v1/deals/${DEAL_ID}`]: () =>
        json(200, deal({ status: 'accepted', role: 'proposer' })),
    })
    renderScreen(<DealCard me={meOf(NINO)} />, { route, path })
    expect(await screen.findByText(/Ваш ход: отправьте/)).toHaveTextContent(
      'Ваш ход: отправьте 1 712,33₾GEL',
    )
    expect(screen.getByText(/Шаг 1 · Nino B → Alex/)).toBeInTheDocument()
    expect(screen.getByText(/Шаг 2 · Alex → Nino B/)).toBeInTheDocument()
    expect(screen.getByText('Наличными при встрече')).toBeInTheDocument()
    expect(screen.getByText(/Курс зафиксирован при предложении/)).toHaveTextContent(
      '1 ₾GEL = 29,20 ₽RUB',
    )
    expect(mainButton()?.text).toBe('Деньги отправлены')
    expect(screen.getByRole('button', { name: 'Отменить сделку' })).toBeInTheDocument()
  })

  it('marks a transfer sent only once that is confirmed', async () => {
    const { served } = fakeApi({
      [`GET /api/v1/deals/${DEAL_ID}`]: () => json(200, deal({ status: 'accepted' })),
      [`POST /api/v1/deals/${DEAL_ID}/legs/1/sent`]: () => json(200, deal({ status: 'leg1_sent' })),
    })
    renderScreen(<DealCard me={meOf(NINO)} />, { route, path })
    await screen.findByText(/Ваш ход/)
    vi.mocked(confirmAction).mockResolvedValueOnce(false)
    press()
    await waitFor(() => {
      expect(confirmAction).toHaveBeenCalledTimes(1)
    })
    expect(served).not.toContain(`POST /api/v1/deals/${DEAL_ID}/legs/1/sent`)
    expect(vi.mocked(confirmAction).mock.calls[0]?.[0]).toBe(
      'Отметить, что вы отправили 1\u00a0712,33 GEL? Отменить отметку нельзя.',
    )
    press()
    await waitFor(() => {
      expect(served).toContain(`POST /api/v1/deals/${DEAL_ID}/legs/1/sent`)
    })
  })

  it('lets the author accept, choosing where to be paid when it isn’t cash', async () => {
    let body: unknown
    fakeApi({
      [`GET /api/v1/deals/${DEAL_ID}`]: () =>
        json(200, {
          ...deal({ role: 'acceptor' }),
          legs: deal().legs.map((leg) => (leg.seq === 1 ? { ...leg, method: 'bank' } : leg)),
        }),
      'GET /api/v1/payment-methods': () =>
        json(200, [
          {
            id: 'e0000000-0000-4000-8000-000000000009',
            asset: 'GEL',
            kind: 'bank',
            title: 'TBC',
            details: { masked: '•••• 7777', full: 'GE29TB7777777777777777' },
            created_at: '2026-10-22T10:00:00Z',
          },
        ]),
      [`POST /api/v1/deals/${DEAL_ID}/accept`]: async (request) => {
        body = await request.json()
        return json(200, deal({ status: 'accepted', role: 'acceptor' }))
      },
    })
    renderScreen(<DealCard me={meOf(ALEX)} />, { route, path })
    expect(
      await screen.findByText('Новое предложение: примите его или отклоните'),
    ).toBeInTheDocument()
    // The payer sees only the mask before accepting (Q-B8).
    expect(screen.getByText(/•••• 5678/)).toHaveTextContent('Реквизиты откроются')
    expect(mainButton()?.text).toBe('Принять')
    press()
    expect(await screen.findByText('Выберите, куда вам заплатить')).toBeInTheDocument()
    fireEvent.click(await screen.findByRole('radio', { name: /TBC/ }))
    press()
    await waitFor(() => {
      expect(body).toEqual({ receive_with: 'e0000000-0000-4000-8000-000000000009' })
    })
  })

  it('tells a stranger only that there is no such deal', async () => {
    fakeApi({ [`GET /api/v1/deals/${DEAL_ID}`]: () => problem(404, 'deal.not_found') })
    renderScreen(<DealCard me={meOf(NINO)} />, { route, path })
    expect(await screen.findByText('Сделка не найдена.')).toBeInTheDocument()
  })
})

describe('the proposal', () => {
  const ORDER: Order = {
    id: 'd0000000-0000-4000-8000-000000000001',
    author: ALEX,
    mine: false,
    give_currency: 'RUB',
    give_country: 'RU',
    amount_min: '10000.00',
    amount_max: '150000.00',
    amount_remaining: '150000.00',
    available_from: '2026-10-22',
    available_until: '2099-11-05',
    payout_methods: ['card', 'cash'],
    wants: [{ currency: 'GEL', country: 'GE' }],
    rate_spec: { v: 1, type: 'fixed', quotes: [{ base: 'GEL', quote: 'RUB', value: '29.20' }] },
    note: null,
    status: 'open',
    created_at: '2026-10-22T10:00:00Z',
    visibility: null,
  }

  it('sends exactly what was chosen, with the counter-amount from the api', async () => {
    let sent: unknown
    fakeApi({
      [`GET /api/v1/orders/${ORDER.id}`]: () => json(200, ORDER),
      'GET /api/v1/payment-methods': () =>
        json(200, [
          {
            id: 'e0000000-0000-4000-8000-000000000001',
            asset: 'RUB',
            kind: 'card',
            title: 'Бабушка',
            details: { masked: '•••• 5678', full: '2202 2061 1234 5678' },
            created_at: '2026-10-22T10:00:00Z',
          },
        ]),
      'POST /api/v1/quote': () => json(200, { amount: '1712.33' }),
      [`POST /api/v1/orders/${ORDER.id}/deals`]: async (request) => {
        sent = await request.json()
        return json(201, deal())
      },
    })
    renderScreen(<ProposeDeal />, {
      route: `/orders/${ORDER.id}/propose`,
      path: '/orders/:id/propose',
    })
    fireEvent.change(await screen.findByRole('textbox', { name: 'Сколько вы хотите получить' }), {
      target: { value: '50 000' },
    })
    await waitFor(() => {
      expect(document.body).toHaveTextContent('Взамен вы отдаёте 1 712,33₾GEL')
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Карта' })[0] as HTMLElement)
    fireEvent.click(await screen.findByRole('radio', { name: /Бабушка/ }))
    fireEvent.click(screen.getAllByRole('button', { name: 'Наличные' })[1] as HTMLElement)
    expect(mainButton()?.text).toBe('Отправить предложение')
    press()
    expect(await screen.findByTestId('elsewhere')).toHaveTextContent(`/deals/${DEAL_ID}`)
    expect(sent).toMatchObject({
      amount: '50000',
      want_currency: 'GEL',
      whole: false,
      first: 'proposer',
      give_method: 'card',
      receive_with: 'e0000000-0000-4000-8000-000000000001',
      counter_method: 'cash',
    })
  })

  it('says what is missing instead of sending', async () => {
    const { served } = fakeApi({
      [`GET /api/v1/orders/${ORDER.id}`]: () => json(200, ORDER),
      'GET /api/v1/payment-methods': () => json(200, []),
    })
    renderScreen(<ProposeDeal />, {
      route: `/orders/${ORDER.id}/propose`,
      path: '/orders/:id/propose',
    })
    fireEvent.change(await screen.findByRole('textbox', { name: 'Сколько вы хотите получить' }), {
      target: { value: '5000' },
    })
    press()
    expect(await screen.findByText(/не меньше минимума заявки/)).toBeInTheDocument()
    expect(served).not.toContain(`POST /api/v1/orders/${ORDER.id}/deals`)
  })
})
