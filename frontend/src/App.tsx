import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { backButton } from '@tma.js/sdk-react'
import { House, Users } from 'lucide-react'
import { useEffect } from 'react'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router'

import { ApiError, type Me } from './api/client'
import { backOverride } from './back'
import { useDeviceTimeZone, useMe } from './api/me'
import { I18nProvider } from './i18n/I18n'
import { resolveLocale } from './i18n/locale'
import { useI18n } from './i18n/useI18n'
import { startRoute } from './routes'
import { Home } from './screens/Home'
import { Invite } from './screens/Invite'
import { Language } from './screens/Language'
import { LinkScreen } from './screens/LinkScreen'
import { Links } from './screens/Links'
import { NewOrder } from './screens/NewOrder'
import { OrderCard } from './screens/OrderCard'
import { PaymentMethodCard } from './screens/PaymentMethodCard'
import { PaymentMethodForm } from './screens/PaymentMethodForm'
import { Profile } from './screens/Profile'
import { OutsideTelegram } from './screens/OutsideTelegram'
import { Problem } from './screens/Problem'
import type { Launch } from './telegram'
import { TabBar } from './ui/TabBar'

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

// The tabs' own screens (Q-B14). Everything else sits above one of them.
const TAB_ROOTS = ['/', '/links']

/** Telegram's BackButton follows the router: hidden on a tab, and it goes back. */
function BackButtonSync() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  useEffect(() => {
    if (!backButton.isMounted()) return
    if (TAB_ROOTS.includes(pathname)) {
      backButton.hide()
      return
    }
    backButton.show()
    return backButton.onClick(() => {
      const stepBack = backOverride()
      if (stepBack) stepBack()
      else void navigate(-1)
    })
  }, [pathname, navigate])
  return null
}

function Tabs() {
  const { t } = useI18n()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  if (!TAB_ROOTS.includes(pathname)) return null
  return (
    <TabBar
      current={pathname}
      // Switching tabs replaces the entry, so history only holds what BackButton undoes.
      onSelect={(path) => void navigate(path, { replace: true })}
      tabs={[
        { path: '/', label: t('tab.home'), icon: <House aria-hidden className="size-6" /> },
        { path: '/links', label: t('tab.links'), icon: <Users aria-hidden className="size-6" /> },
      ]}
    />
  )
}

function Screens({ me, startParam }: { me: Me; startParam: string | undefined }) {
  // A deep link opens its card above Home, so BackButton leads Home (ADR-0013).
  const start = startRoute(startParam)
  return (
    <MemoryRouter initialEntries={start ? ['/', start] : ['/']} initialIndex={start ? 1 : 0}>
      <BackButtonSync />
      <Routes>
        <Route path="/" element={<Home me={me} />} />
        <Route path="/links" element={<Links />} />
        <Route path="/links/invite" element={<Invite />} />
        <Route path="/links/:id" element={<LinkScreen />} />
        <Route path="/orders/new" element={<NewOrder />} />
        <Route path="/orders/:id" element={<OrderCard />} />
        <Route path="/profile" element={<Profile me={me} />} />
        <Route path="/profile/details/new" element={<PaymentMethodForm />} />
        <Route path="/profile/details/:id" element={<PaymentMethodCard />} />
        <Route path="/language" element={<Language />} />
      </Routes>
      <Tabs />
    </MemoryRouter>
  )
}

function SignedIn({ launch }: { launch: Launch }) {
  const me = useMe()
  useDeviceTimeZone(me.data)
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
        <Screens me={me.data} startParam={launch.startParam} />
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
