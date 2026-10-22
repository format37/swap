import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import type { Me } from './api/client'
import { App } from './App'
import { useMainButton } from './telegram'
import { Home } from './screens/Home'
import { fakeApi, json } from './test/api'
import { renderScreen } from './test/render'

vi.mock('./telegram', () => ({
  useMainButton: vi.fn(),
  hapticNotify: vi.fn(),
  hapticSelect: vi.fn(),
  openPage: vi.fn(),
}))

const me: Me = {
  id: '6f1c9a52-0d7e-4d53-9d0c-8f6f3e2b7c11',
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
  photo_url: null,
  score: 0,
  locale: 'ru',
  locale_chosen: false,
  tz: 'Asia/Tbilisi',
  notifications_off: false,
  muted_kinds: [],
  terms_accepted: true,
}

function quietApi() {
  fakeApi({
    'GET /api/v1/links': () => json(200, { active: [], incoming: [], outgoing: [], invites: [] }),
    'GET /api/v1/orders': () => json(200, []),
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

it('outside Telegram, points to the bot in the browser’s language', () => {
  render(<App launch={null} />)
  // jsdom's navigator.language is en-US.
  expect(screen.getByRole('heading')).toHaveTextContent('Open Swap in Telegram')
  expect(screen.getByRole('link')).toHaveAttribute('href', 'https://t.me/peertopeerswapbot')
})

it('greets the user by name, in their language', () => {
  quietApi()
  renderScreen(<Home me={me} />)
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Привет, Alex!')
  expect(screen.getByText('@format37')).toBeInTheDocument()
  // The profile, with the language, opens from the avatar (Q-B14).
  expect(screen.getByRole('button', { name: 'Профиль' })).toBeInTheDocument()
})

it('speaks Georgian when asked to', () => {
  quietApi()
  renderScreen(<Home me={me} />, { locale: 'ka' })
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('გამარჯობა, Alex!')
  expect(screen.getByRole('button', { name: 'პროფილი' })).toBeInTheDocument()
})

it('asks for the agreement before anything else, once (Q-B15, K3)', async () => {
  let accepted = false
  const { served } = fakeApi({
    'GET /api/v1/me': () => json(200, { ...me, terms_accepted: accepted }),
    'POST /api/v1/me/terms': () => {
      accepted = true
      return json(200, { ...me, terms_accepted: true })
    },
    'GET /api/v1/links': () => json(200, { active: [], incoming: [], outgoing: [], invites: [] }),
    'GET /api/v1/orders': () => json(200, []),
    'GET /api/v1/deals': () => json(200, []),
  })
  render(<App launch={{ initDataRaw: 'query_id=x', languageCode: 'ru', startParam: undefined }} />)
  expect(await screen.findByRole('heading', { name: 'Прежде чем начать' })).toBeInTheDocument()
  expect(served).not.toContain('GET /api/v1/orders')
  const accept = vi.mocked(useMainButton).mock.lastCall?.[0]
  expect(accept?.text).toBe('Принимаю')
  act(() => {
    accept?.onClick()
  })
  expect(await screen.findByRole('heading', { name: 'Привет, Alex!' })).toBeInTheDocument()
  await waitFor(() => {
    expect(served).toContain('POST /api/v1/me/terms')
  })
})
