import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { fakeApi, json } from '../test/api'
import type { Me } from './client'
import { useDeviceTimeZone } from './me'

const me: Me = {
  id: '6f1c9a52-0d7e-4d53-9d0c-8f6f3e2b7c11',
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
  photo_url: null,
  locale: 'ru',
  locale_chosen: false,
  tz: null,
}

function Probe({ who }: { who: Me }) {
  useDeviceTimeZone(who)
  return null
}

function renderProbe(who: Me) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <Probe who={who} />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

it('sends the device time zone when the server has none', async () => {
  let body: unknown
  const { served } = fakeApi({
    'PATCH /api/v1/me': async (request) => {
      body = await request.json()
      return json(200, { ...me, tz: 'Asia/Tbilisi' })
    },
  })
  renderProbe(me)
  await waitFor(() => {
    expect(served).toContain('PATCH /api/v1/me')
  })
  expect(body).toEqual({ tz: Intl.DateTimeFormat().resolvedOptions().timeZone })
})

it('leaves a time zone the server already has alone', async () => {
  const { served } = fakeApi({})
  renderProbe({ ...me, tz: 'Asia/Tbilisi' })
  await new Promise((resolve) => setTimeout(resolve, 20))
  expect(served).toEqual([])
})
