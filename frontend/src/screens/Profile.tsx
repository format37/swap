import { Globe } from 'lucide-react'
import { useNavigate } from 'react-router'

import type { Me } from '../api/client'
import { useI18n } from '../i18n/useI18n'
import { LANGUAGE_NAMES } from '../i18n/locale'
import { Avatar } from '../ui/Avatar'
import { Cell } from '../ui/Cell'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/**
 * The profile behind Home's avatar (Q-B14): who I am and my language. No payment details:
 * the parties settle where to pay among themselves (QUESTIONS G3).
 */
export function Profile({ me }: { me: Me }) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const name = [me.first_name, me.last_name].filter(Boolean).join(' ')

  return (
    <Screen>
      <header className="flex flex-col items-center gap-2 px-6 pt-8 text-center">
        <Avatar name={name} size="xl" />
        <h1 className="text-2xl font-semibold">{name}</h1>
        {me.username && <p className="text-hint">@{me.username}</p>}
      </header>

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
