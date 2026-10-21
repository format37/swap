import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'

import { I18nProvider } from '../i18n/I18n'
import type { Locale } from '../i18n/locale'

/** Shows where the app went, for tests that follow a navigation. */
function Elsewhere() {
  const { pathname } = useLocation()
  return <p data-testid="elsewhere">{pathname}</p>
}

interface Options {
  route?: string
  path?: string
  /** What the screen finds in `location.state`, as navigate(…, { state }) leaves it. */
  state?: unknown
  locale?: Locale
}

/** One screen at `route`, matched by `path`, with the providers the app gives it. */
export function renderScreen(
  screen: ReactNode,
  { route = '/', path = route, state, locale = 'ru' }: Options = {},
) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <I18nProvider locale={locale}>
        <MemoryRouter initialEntries={[{ pathname: route, state }]}>
          <Routes>
            <Route path={path} element={screen} />
            <Route path="*" element={<Elsewhere />} />
          </Routes>
        </MemoryRouter>
      </I18nProvider>
    </QueryClientProvider>,
  )
}
