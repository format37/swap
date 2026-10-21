import { vi } from 'vitest'

import { setLaunchInitData } from '../api/client'

type Handler = (request: Request) => Response | Promise<Response>

export function json(status: number, body: unknown): Response {
  const type = status >= 400 ? 'application/problem+json' : 'application/json'
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': type } })
}

export function problem(status: number, code: string): Response {
  return json(status, { type: 'about:blank', title: 'Problem', status, code })
}

/**
 * A stand-in for the api on `fetch`: routes by "METHOD /path", signs in on its own, and
 * records every request it served.
 */
export function fakeApi(routes: Record<string, Handler>) {
  const served: string[] = []
  const fetchMock = vi.fn((input: Request) => {
    const route = `${input.method} ${new URL(input.url).pathname}`
    if (route === 'POST /api/v1/auth/telegram')
      return Promise.resolve(json(200, { token: 'tok', expires_at: '2026-10-23T00:00:00Z' }))
    served.push(route)
    const handler = routes[route]
    return Promise.resolve(handler ? handler(input) : problem(404, 'not_found'))
  })
  vi.stubGlobal('fetch', fetchMock)
  setLaunchInitData('query_id=AAH&user=%7B%7D&auth_date=1&hash=abc')
  return { served }
}
