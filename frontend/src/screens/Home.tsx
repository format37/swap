import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import type { Me } from '../api/client'
import { useLinks } from '../api/links'
import { useDeals } from '../api/deals'
import { useOrders, type Order } from '../api/orders'
import { DealRow } from '../deals/DealRow'
import { useI18n } from '../i18n/useI18n'
import { OrderRow } from '../orders/OrderRow'
import { useMainButton } from '../telegram'
import { Avatar } from '../ui/Avatar'
import { EmptyState } from '../ui/EmptyState'
import { PersonRow } from '../ui/Person'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/**
 * «Главная» (§11): link requests waiting for me, then orders open to me, then mine. With
 * nothing at all, the three steps that explain Swap.
 */
export function Home({ me }: { me: Me }) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const links = useLinks()
  const open = useOrders('visible')
  const mine = useOrders('mine')
  const past = useOrders('history')
  const deals = useDeals('active')

  useMainButton({
    text: t('home.new_order'),
    onClick: () => void navigate('/orders/new'),
  })

  const incoming = links.data?.incoming ?? []
  const linked = (links.data?.active.length ?? 0) > 0
  const loaded =
    links.isSuccess && open.isSuccess && mine.isSuccess && past.isSuccess && deals.isSuccess
  const nothing =
    loaded &&
    !linked &&
    !incoming.length &&
    !open.data.length &&
    !mine.data.length &&
    !past.data.length &&
    !deals.data.length

  return (
    <Screen tabs>
      <header className="flex items-center gap-4 px-6 pt-4">
        {/* The profile opens from the avatar (Q-B14). */}
        <button
          type="button"
          aria-label={t('profile.title')}
          onClick={() => void navigate('/profile')}
          className="rounded-full active:opacity-70"
        >
          <Avatar name={me.first_name} photo={me.photo_url} />
        </button>
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
            <PersonRow
              key={link.id}
              person={link.person}
              detail={t('link.incoming')}
              onClick={() => void navigate(`/links/${link.id}`)}
            />
          ))}
        </Section>
      )}

      {deals.data && deals.data.length > 0 && (
        <Section title={t('home.deals')}>
          {deals.data.map((deal) => (
            <DealRow
              key={deal.id}
              deal={deal}
              me={me.id}
              onOpen={() => void navigate(`/deals/${deal.id}`)}
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
          {past.data && past.data.length > 0 && (
            <Past orders={past.data} onOpen={(id) => void navigate(`/orders/${id}`)} />
          )}
        </>
      )}
    </Screen>
  )
}

/**
 * Finished orders, mine and those I had a deal on, folded away under one line: kept to
 * look back on, out of the way of what is open (QUESTIONS H4).
 */
function Past({ orders, onOpen }: { orders: Order[]; onOpen: (id: string) => void }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const Chevron = open ? ChevronDown : ChevronRight
  return (
    <Section>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => {
          setOpen(!open)
        }}
        className="flex w-full items-center gap-3 px-4 py-3 text-left active:bg-secondary-bg"
      >
        <span className="min-w-0 flex-1">{t('home.past', { count: orders.length })}</span>
        <Chevron aria-hidden className="size-5 shrink-0 text-hint" />
      </button>
      {open &&
        orders.map((order) => (
          <OrderRow
            key={order.id}
            order={order}
            onOpen={() => {
              onOpen(order.id)
            }}
          />
        ))}
    </Section>
  )
}
