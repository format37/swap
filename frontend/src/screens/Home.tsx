import { Globe, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router'

import type { Me } from '../api/client'
import { fullName, useLinks } from '../api/links'
import { useOrders } from '../api/orders'
import { useI18n } from '../i18n/useI18n'
import { LANGUAGE_NAMES } from '../i18n/locale'
import { OrderRow } from '../orders/OrderRow'
import { useMainButton } from '../telegram'
import { Avatar } from '../ui/Avatar'
import { Cell } from '../ui/Cell'
import { EmptyState } from '../ui/EmptyState'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/**
 * «Главная» (§11): link requests waiting for me, then orders open to me, then mine. With
 * nothing at all, the three steps that explain Swap.
 */
export function Home({ me }: { me: Me }) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const links = useLinks()
  const open = useOrders('visible')
  const mine = useOrders('mine')

  useMainButton({
    text: t('home.new_order'),
    onClick: () => void navigate('/orders/new'),
  })

  const incoming = links.data?.incoming ?? []
  const linked = (links.data?.active.length ?? 0) > 0
  const loaded = links.isSuccess && open.isSuccess && mine.isSuccess
  const nothing = loaded && !linked && !incoming.length && !open.data.length && !mine.data.length

  return (
    <Screen tabs>
      <header className="flex items-center gap-4 px-6 pt-4">
        <Avatar name={me.first_name} />
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold">
            {t('home.hello', { name: me.first_name })}
          </h1>
          {me.username && <p className="truncate text-hint">@{me.username}</p>}
        </div>
      </header>

      {incoming.length > 0 && (
        <Section title={t('home.link_requests')}>
          {incoming.map((link) => (
            <Cell
              key={link.id}
              icon={<Avatar name={fullName(link.person)} size="sm" />}
              label={fullName(link.person)}
              subtitle={t('link.incoming')}
              opens
              onClick={() => void navigate(`/links/${link.id}`)}
            />
          ))}
        </Section>
      )}

      {nothing ? (
        <>
          <p className="px-6 text-hint">{t('home.intro')}</p>
          <EmptyState
            icon={<Sparkles aria-hidden className="size-12" />}
            title={t('home.empty.title')}
            steps={[t('home.empty.step1'), t('home.empty.step2'), t('home.empty.step3')]}
          />
        </>
      ) : (
        <>
          {open.data && (open.data.length > 0 || linked) && (
            <Section title={t('home.open_to_me')}>
              {open.data.length > 0 ? (
                open.data.map((order) => (
                  <OrderRow
                    key={order.id}
                    order={order}
                    onOpen={() => void navigate(`/orders/${order.id}`)}
                  />
                ))
              ) : (
                <p className="px-4 py-3 text-hint">{t('home.nothing_open')}</p>
              )}
            </Section>
          )}
          {mine.data && mine.data.length > 0 && (
            <Section title={t('home.mine')}>
              {mine.data.map((order) => (
                <OrderRow
                  key={order.id}
                  order={order}
                  onOpen={() => void navigate(`/orders/${order.id}`)}
                />
              ))}
            </Section>
          )}
        </>
      )}

      <Section title={t('home.settings')}>
        <Cell
          icon={<Globe aria-hidden className="size-6" />}
          label={t('settings.language')}
          detail={LANGUAGE_NAMES[locale]}
          opens
          onClick={() => void navigate('/language')}
        />
      </Section>
    </Screen>
  )
}
