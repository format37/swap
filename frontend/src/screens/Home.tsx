import { Globe } from 'lucide-react'
import { useNavigate } from 'react-router'

import type { Me } from '../api/client'
import { useI18n } from '../i18n/useI18n'
import { LANGUAGE_NAMES } from '../i18n/locale'
import { Avatar } from '../ui/Avatar'
import { Cell } from '../ui/Cell'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

export function Home({ me }: { me: Me }) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
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
      <p className="px-6 text-hint">{t('home.intro')}</p>
      <Section title={t('settings.title')}>
        <Cell
          icon={<Globe aria-hidden className="size-6" />}
          label={t('settings.language')}
          detail={LANGUAGE_NAMES[locale]}
          opens
          onClick={() => void navigate('/language')}
        />
      </Section>
      <p className="px-6 text-sm text-hint">{t('home.soon')}</p>
    </Screen>
  )
}
