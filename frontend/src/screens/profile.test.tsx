import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Me } from '../api/client'
import { fakeApi, json } from '../test/api'
import { renderScreen } from '../test/render'
import { fullName } from '../api/links'
import { Person } from '../ui/Person'
import { Notifications } from './Notifications'
import { Profile } from './Profile'

vi.mock('../telegram', () => ({
  confirmAction: vi.fn(() => Promise.resolve(true)),
  hapticNotify: vi.fn(),
  hapticSelect: vi.fn(),
  explain: vi.fn(() => Promise.resolve()),
}))

const me: Me = {
  id: 'a0000000-0000-4000-8000-000000000002',
  first_name: 'Nino',
  last_name: 'B',
  username: 'nino',
  photo_url: null,
  score: 0,
  locale: 'ru',
  locale_chosen: false,
  tz: 'Asia/Tbilisi',
  notifications_off: false,
  muted_kinds: [],
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('the profile', () => {
  it('shows who I am and my language, and asks for no payment details', () => {
    const { served } = fakeApi({})
    renderScreen(<Profile me={me} />, { route: '/profile' })
    expect(screen.getByRole('heading', { name: 'Nino B' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Язык.*Русский/ })).toBeInTheDocument()
    // The parties settle where to pay among themselves (QUESTIONS G3).
    expect(screen.queryByText(/Реквизиты/)).toBeNull()
    expect(served).toEqual([])
  })
})

describe('the notification settings (K1)', () => {
  it('says on the profile whether they are on', () => {
    fakeApi({})
    renderScreen(<Profile me={{ ...me, muted_kinds: ['orders'] }} />, { route: '/profile' })
    expect(screen.getByRole('button', { name: /Уведомления.*Частично/ })).toBeInTheDocument()
  })

  it('switches kinds off one by one, and everything at once', async () => {
    const sent: unknown[] = []
    fakeApi({
      'PATCH /api/v1/me': async (request) => {
        const body = (await request.json()) as Partial<Me>
        sent.push(body)
        return json(200, { ...me, ...body })
      },
    })
    const { unmount } = renderScreen(<Notifications me={me} />)
    expect(screen.getAllByRole('switch')).toHaveLength(6)
    fireEvent.click(screen.getByRole('switch', { name: 'Переводы' }))
    await waitFor(() => {
      expect(sent).toEqual([{ muted_kinds: ['transfers'] }])
    })
    fireEvent.click(screen.getByRole('switch', { name: 'Все уведомления' }))
    await waitFor(() => {
      expect(sent).toContainEqual({ notifications_off: true })
    })
    // With everything off, the kinds have nothing to say.
    unmount()
    renderScreen(<Notifications me={{ ...me, notifications_off: true }} />)
    expect(screen.queryByRole('switch', { name: 'Переводы' })).toBeNull()
  })
})

describe('deleting (K2)', () => {
  it('deletes all finished history and says what still runs', async () => {
    const { served } = fakeApi({
      'DELETE /api/v1/me/history': () => json(200, { deals: 3, orders: 1, running: 2 }),
    })
    renderScreen(<Profile me={me} />, { route: '/profile' })
    fireEvent.click(screen.getByRole('button', { name: 'Удалить всю историю' }))
    expect(
      await screen.findByText('Удалено сделок: 3, заявок: 1. Ещё идут и остались: 2.'),
    ).toBeInTheDocument()
    expect(served).toContain('DELETE /api/v1/me/history')
  })

  it('deletes the account, then has nothing more to ask of the api', async () => {
    const onGone = vi.fn()
    const { served } = fakeApi({ 'DELETE /api/v1/me': () => new Response(null, { status: 204 }) })
    renderScreen(<Profile me={me} onGone={onGone} />, { route: '/profile' })
    fireEvent.click(screen.getByRole('button', { name: 'Удалить аккаунт' }))
    await waitFor(() => {
      expect(onGone).toHaveBeenCalled()
    })
    expect(served).toEqual(['DELETE /api/v1/me'])
  })

  it('says why an account with a running deal stays', async () => {
    fakeApi({
      'DELETE /api/v1/me': () =>
        json(409, { type: 'about:blank', title: 'x', status: 409, code: 'account.deals_running' }),
    })
    renderScreen(<Profile me={me} />, { route: '/profile' })
    fireEvent.click(screen.getByRole('button', { name: 'Удалить аккаунт' }))
    expect(
      await screen.findByText(
        'Сначала завершите идущие сделки: пока они идут, аккаунт удалить нельзя.',
      ),
    ).toBeInTheDocument()
  })

  it('names someone who left «Удалённый участник»', () => {
    fakeApi({})
    const gone = {
      id: 'a0000000-0000-4000-8000-000000000009',
      first_name: '',
      last_name: null,
      username: null,
      photo_url: null,
      score: 1,
      deleted: true,
    }
    renderScreen(<Person person={gone} />)
    expect(fullName(gone)).toBe('Удалённый участник')
    expect(screen.getByText('Удалённый участник')).toBeInTheDocument()
  })
})
