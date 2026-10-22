import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { api, ApiError, setLaunchInitData, unwrap } from './client'

const me = {
  id: '6f1c9a52-0d7e-4d53-9d0c-8f6f3e2b7c11',
  first_name: 'Alex',
  last_name: null,
  username: 'format37',
  locale: 'ru',
  locale_chosen: false,
  telegram_locale: 'ru',
}

function json(status: number, body: unknown, type = 'application/json') {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': type } })
}

const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  setLaunchInitData('query_id=AAH&user=%7B%7D&auth_date=1&hash=abc')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function requested(call: number): Request {
  const request = fetchMock.mock.calls[call]?.[0]
  if (!(request instanceof Request)) throw new Error(`call ${call} was not a Request`)
  return request
}

it('signs in once with the launch initData, then sends the bearer token', async () => {
  fetchMock.mockImplementation((input) => {
    const url = input instanceof Request ? input.url : String(input)
    return Promise.resolve(
      url.endsWith('/auth/telegram')
        ? json(200, { token: 'tok', expires_at: '2026-10-22T12:00:00Z', me })
        : json(200, me),
    )
  })

  await expect(unwrap(api.GET('/api/v1/me'))).resolves.toEqual(me)
  await unwrap(api.GET('/api/v1/me'))

  expect(fetchMock).toHaveBeenCalledTimes(3)
  expect(requested(0).url).toMatch(/\/api\/v1\/auth\/telegram$/)
  expect(await requested(0).json()).toEqual({
    init_data: 'query_id=AAH&user=%7B%7D&auth_date=1&hash=abc',
  })
  expect(requested(1).headers.get('Authorization')).toBe('Bearer tok')
  expect(requested(2).headers.get('Authorization')).toBe('Bearer tok')
})

it('turns a problem response into an ApiError with its code', async () => {
  fetchMock.mockResolvedValue(
    json(
      401,
      { type: 'about:blank', title: 'Unauthorized', status: 401, code: 'init_data_expired' },
      'application/problem+json',
    ),
  )
  const failure = unwrap(api.GET('/api/v1/me'))
  await expect(failure).rejects.toBeInstanceOf(ApiError)
  await expect(failure).rejects.toMatchObject({ status: 401, code: 'init_data_expired' })
})

it('reports a dead network as code "network"', async () => {
  fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
  await expect(unwrap(api.GET('/api/v1/me'))).rejects.toMatchObject({ status: 0, code: 'network' })
})

it('without initData there is no sign-in to try', async () => {
  setLaunchInitData(undefined)
  await expect(unwrap(api.GET('/api/v1/me'))).rejects.toMatchObject({
    code: 'init_data_missing',
  })
  expect(fetchMock).not.toHaveBeenCalled()
})
