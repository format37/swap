import { Globe, Plus, WalletCards } from 'lucide-react'
import { useNavigate } from 'react-router'

import type { Me } from '../api/client'
import { usePaymentMethods, type PaymentMethod } from '../api/payments'
import { useI18n } from '../i18n/useI18n'
import { LANGUAGE_NAMES } from '../i18n/locale'
import { Asset } from '../money/Asset'
import { KINDS } from '../money/kinds'
import { Avatar } from '../ui/Avatar'
import { Button } from '../ui/Button'
import { Cell } from '../ui/Cell'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/** The profile behind Home's avatar (Q-B14): who I am, my payment details, my language. */
export function Profile({ me }: { me: Me }) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const methods = usePaymentMethods()
  const name = [me.first_name, me.last_name].filter(Boolean).join(' ')

  return (
    <Screen>
      <header className="flex flex-col items-center gap-2 px-6 pt-8 text-center">
        <Avatar name={name} size="xl" />
        <h1 className="text-2xl font-semibold">{name}</h1>
        {me.username && <p className="text-hint">@{me.username}</p>}
      </header>

      <Section title={t('profile.details')}>
        {methods.data?.length === 0 && <p className="px-4 py-3 text-hint">{t('details.empty')}</p>}
        {methods.data?.map((method) => (
          <MethodRow
            key={method.id}
            method={method}
            onOpen={() => void navigate(`/profile/details/${method.id}`)}
          />
        ))}
      </Section>
      <div className="mx-4">
        <Button
          icon={<Plus aria-hidden className="size-5" />}
          onClick={() => void navigate('/profile/details/new')}
        >
          {t('profile.add_details')}
        </Button>
      </div>
      <p className="px-6 text-sm text-hint">{t('profile.details_hint')}</p>

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

function MethodRow({ method, onOpen }: { method: PaymentMethod; onOpen: () => void }) {
  const { t } = useI18n()
  const Icon = KINDS.find(({ kind }) => kind === method.kind)?.icon ?? WalletCards
  return (
    <Cell
      icon={<Icon aria-hidden className="size-6" />}
      label={method.title}
      subtitle={
        <span className="flex items-center gap-1.5">
          <Asset code={method.asset} />
          <span>· {method.details?.masked ?? t('details.no_text')}</span>
        </span>
      }
      opens
      onClick={onOpen}
    />
  )
}
