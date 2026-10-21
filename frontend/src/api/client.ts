import createClient, { type Middleware } from 'openapi-fetch'

import type { components, paths } from './schema'

export type Me = components['schemas']['Me']

/** A refused or failed request. `code` is the api's machine code, or "network". */
export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string) {
    super(code)
    this.status = status
    this.code = code
  }
}

const options = {
  // Absolute, because openapi-fetch builds a Request, which needs one outside a browser.
  baseUrl: globalThis.location.origin,
  // Looked up at call time rather than captured at import, so tests can stand in for it.
  fetch: (request: Request) => globalThis.fetch(request),
}

const publicApi = createClient<paths>(options)
export const api = createClient<paths>(options)

let launchInitData: string | undefined
let token: string | null = null
let signingIn: Promise<string> | null = null

/** This launch's initData, which every sign-in sends (ADR-0011). */
export function setLaunchInitData(raw: string | undefined): void {
  launchInitData = raw
  token = null
}

async function session(): Promise<string> {
  if (token) return token
  signingIn ??= (async () => {
    if (!launchInitData) throw new ApiError(401, 'init_data_missing')
    const signed = await unwrap(
      publicApi.POST('/api/v1/auth/telegram', { body: { init_data: launchInitData } }),
    )
    token = signed.token
    return signed.token
  })().finally(() => {
    signingIn = null
  })
  return signingIn
}

// The token lives in memory only: one session per launch, no cookie (ADR-0011).
const auth: Middleware = {
  async onRequest({ request }) {
    request.headers.set('Authorization', `Bearer ${await session()}`)
    return request
  },
  onResponse({ response }) {
    // The session is gone on the server; the next request signs in again.
    if (response.status === 401) token = null
    return response
  },
}
api.use(auth)

interface Result<T> {
  data?: T
  error?: unknown
  response: Response
}

/** The data of a successful response; an ApiError carrying the problem's code otherwise. */
export async function unwrap<T>(request: Promise<Result<T>>): Promise<T> {
  let result: Result<T>
  try {
    result = await request
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(0, 'network')
  }
  const { data, error, response } = result
  if (response.ok && data !== undefined) return data
  throw new ApiError(response.status, problemCode(error) ?? 'unknown')
}

function problemCode(body: unknown): string | undefined {
  if (typeof body === 'object' && body !== null && 'code' in body && typeof body.code === 'string')
    return body.code
  return undefined
}
