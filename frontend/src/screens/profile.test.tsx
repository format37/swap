import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Me } from '../api/client'
import type { PaymentMethod } from '../api/payments'
import { confirmAction, copyText, useMainButton, type MainAction } from '../telegram'
import { fakeApi, json, problem } from '../test/api'
import { renderScreen } from '../test/render'
import { PaymentMethodCard } from './PaymentMethodCard'
import { PaymentMethodForm } from './PaymentMethodForm'
import { Profile } from './Profile'

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

const me: Me = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
  locale: 'ru',
  locale_chosen: false,
  tz: 'Asia/Tbilisi',
}

const TBC: PaymentMethod = {
  id: 'e0000000-0000-4000-8000-000000000001',
  asset: 'GEL',
  kind: 'bank',
  title: 'TBC',
  details: { masked: '•••• 7777', full: 'IBAN GE29TB7777777777777777, Нино Б.' },
  created_at: '2026-10-22T10:00:00Z',
}
const CASH: PaymentMethod = {
  ...TBC,
  id: 'e0000000-0000-4000-8000-000000000002',
  kind: 'cash',
  title: 'Наличные',
  details: null,
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('the profile', () => {
  it('lists payment details by their mask, and the language', async () => {
    fakeApi({ 'GET /api/v1/payment-methods': () => json(200, [TBC, CASH]) })
    renderScreen(<Profile me={me} />, { route: '/profile' })
    expect(await screen.findByRole('button', { name: /TBC.*GEL.*•••• 7777/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Наличные.*Без реквизитов/ })).toBeInTheDocument()
    // The full text is for the entry's own screen, not the list.
    expect(screen.queryByText(/GE29TB/)).toBeNull()
    expect(screen.getByRole('button', { name: /Язык.*Русский/ })).toBeInTheDocument()
  })
})

describe('new payment details', () => {
  it('needs the text for a card or a bank, and saves exactly what was typed', async () => {
    let saved: unknown
    fakeApi({
      'GET /api/v1/assets': () => json(200, ['RUB', 'GEL', 'USDT']),
      'POST /api/v1/payment-methods': async (request) => {
        saved = await request.json()
        return json(201, TBC)
      },
    })
    renderScreen(<PaymentMethodForm />, { route: '/profile/details/new' })
    await screen.findByRole('option', { name: '₾ GEL' })
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'GEL' } })
    fireEvent.click(screen.getByRole('button', { name: 'Банк' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Название' }), {
      target: { value: ' TBC ' },
    })
    act(() => {
      mainButton()?.onClick()
    })
    expect(await screen.findByText(/Впишите реквизиты/)).toBeInTheDocument()

    fireEvent.change(screen.getByRole('textbox', { name: 'Реквизиты' }), {
      target: { value: 'IBAN GE29TB7777777777777777' },
    })
    act(() => {
      mainButton()?.onClick()
    })
    await waitFor(() => {
      expect(saved).toEqual({
        asset: 'GEL',
        kind: 'bank',
        title: 'TBC',
        text: 'IBAN GE29TB7777777777777777',
      })
    })
  })

  it('warns about the network for crypto', () => {
    fakeApi({ 'GET /api/v1/assets': () => json(200, ['USDT']) })
    renderScreen(<PaymentMethodForm />, { route: '/profile/details/new' })
    fireEvent.click(screen.getByRole('button', { name: 'Крипто' }))
    expect(screen.getByText(/Проверьте сеть/)).toBeInTheDocument()
  })

  it('says when the server can’t save them', async () => {
    fakeApi({
      'GET /api/v1/assets': () => json(200, ['GEL']),
      'POST /api/v1/payment-methods': () => problem(503, 'payment.unavailable'),
    })
    renderScreen(<PaymentMethodForm />, { route: '/profile/details/new' })
    await screen.findByRole('option', { name: '₾ GEL' })
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'GEL' } })
    fireEvent.click(screen.getByRole('button', { name: 'Наличные' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Название' }), {
      target: { value: 'Наличные' },
    })
    act(() => {
      mainButton()?.onClick()
    })
    expect(await screen.findByText(/не сохраняются/)).toBeInTheDocument()
  })
})

describe('an entry', () => {
  const route = `/profile/details/${TBC.id}`
  const path = '/profile/details/:id'

  it('shows its text in full to its owner, to copy', async () => {
    fakeApi({ 'GET /api/v1/payment-methods': () => json(200, [TBC]) })
    renderScreen(<PaymentMethodCard />, { route, path })
    expect(await screen.findByText(/GE29TB7777777777777777/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Скопировать' }))
    await waitFor(() => {
      expect(copyText).toHaveBeenCalledWith(TBC.details?.full)
    })
    expect(await screen.findByRole('button', { name: 'Скопировано' })).toBeInTheDocument()
  })

  it('is deleted once that is confirmed', async () => {
    const { served } = fakeApi({
      'GET /api/v1/payment-methods': () => json(200, [TBC]),
      [`DELETE /api/v1/payment-methods/${TBC.id}`]: () => new Response(null, { status: 204 }),
    })
    renderScreen(<PaymentMethodCard />, { route, path })
    fireEvent.click(await screen.findByRole('button', { name: 'Удалить' }))
    await waitFor(() => {
      expect(served).toContain(`DELETE /api/v1/payment-methods/${TBC.id}`)
    })
    expect(confirmAction).toHaveBeenCalledWith(
      'Удалить эти реквизиты? Начатые сделки сохранят свою копию.',
      'Удалить',
      { destructive: true },
    )
  })
})
