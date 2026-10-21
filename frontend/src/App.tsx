import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { backButton } from '@tma.js/sdk-react'
import { useEffect } from 'react'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router'

import { ApiError, type Me } from './api/client'
import { useMe } from './api/me'
import { I18nProvider } from './i18n/I18n'
import { resolveLocale } from './i18n/locale'
import { Home } from './screens/Home'
import { Language } from './screens/Language'
import { OutsideTelegram } from './screens/OutsideTelegram'
import { Problem } from './screens/Problem'
import type { Launch } from './telegram'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // A refusal won't change on retry, except a 401, which signs in again once.
      retry: (failures, error) =>
        error instanceof ApiError && error.status >= 400 && error.status < 500
          ? error.status === 401 && failures < 1
          : failures < 2,
      refetchOnWindowFocus: false,
    },
  },
})

/** Telegram's BackButton follows the router: shown off Home, and it goes back. */
function BackButtonSync() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  useEffect(() => {
    if (!backButton.isMounted()) return
    if (pathname === '/') {
      backButton.hide()
      return
    }
    backButton.show()
    return backButton.onClick(() => void navigate(-1))
  }, [pathname, navigate])
  return null
}

function Screens({ me }: { me: Me }) {
  return (
    <MemoryRouter>
      <BackButtonSync />
      <Routes>
        <Route path="/" element={<Home me={me} />} />
        <Route path="/language" element={<Language />} />
      </Routes>
    </MemoryRouter>
  )
}

function SignedIn({ launch }: { launch: Launch }) {
  const me = useMe()
  // Until /me answers, Telegram's language; afterwards the api's resolved one.
  const locale = resolveLocale(me.data?.locale, launch.languageCode)
  return (
    <I18nProvider locale={locale}>
      {me.isPending ? (
        <div aria-busy className="screen flex items-center justify-center">
          <img src="/icon.svg" alt="" width={56} height={56} className="animate-pulse" />
        </div>
      ) : me.isError ? (
        <Problem error={me.error} retry={() => void me.refetch()} />
      ) : (
        <Screens me={me.data} />
      )}
    </I18nProvider>
  )
}

export function App({ launch }: { launch: Launch | null }) {
  if (!launch) return <OutsideTelegram />
  return (
    <QueryClientProvider client={queryClient}>
      <SignedIn launch={launch} />
    </QueryClientProvider>
  )
}
