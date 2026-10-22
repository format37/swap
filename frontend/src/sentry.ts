import * as Sentry from '@sentry/react'

/**
 * Error reports (ADR-0025), when the build was given a DSN.
 *
 * Telegram puts the launch's initData in the URL's hash, and the MemoryRouter never
 * changes the URL, so the hash would ride along with every report: it goes first.
 */
export function startSentry(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) return
  Sentry.init({
    dsn,
    environment: import.meta.env.PROD ? 'prod' : 'dev',
    release: import.meta.env.VITE_SENTRY_RELEASE,
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpBodies: [],
      urlQueryParams: false,
    },
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
    beforeSend: withoutLaunchData,
    beforeSendSpan: withoutLaunchData,
    beforeBreadcrumb: withoutLaunchData,
  })
}

export function withoutLaunchData<T>(item: T): T {
  const hash = window.location.hash
  if (hash.length < 2) return item
  // The hash as it appears inside a JSON string, quotes and escapes included.
  const quoted = JSON.stringify(hash).slice(1, -1)
  return JSON.parse(JSON.stringify(item).replaceAll(quoted, '')) as T
}
