import { Check, Globe } from 'lucide-react'
import { useNavigate } from 'react-router'

import type { Me } from '../api/client'
import { useSetLocale } from '../api/me'
import { useI18n } from '../i18n/useI18n'
import { LANGUAGE_NAMES, LOCALES, type Locale } from '../i18n/locale'
import { hapticSelect } from '../telegram'
import { Cell } from '../ui/Cell'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/**
 * Each language in its own script, so it can be found from any of them (ADR-0009). First
 * comes «Как в Telegram», which lets a choice go and follows Telegram again (ADR-0039).
 */
export function Language({ me }: { me: Me }) {
  const { t } = useI18n()
  const setLocale = useSetLocale()
  const navigate = useNavigate()
  const choose = (locale: Locale | null) => {
    hapticSelect()
    setLocale.mutate(locale, { onSuccess: () => void navigate(-1) })
  }
  const mark = (on: boolean) => (on ? <Check aria-hidden className="size-5 text-accent" /> : null)
  return (
    <Screen>
      <h1 className="flex items-center gap-2 px-6 pt-4 text-2xl font-semibold">
        <Globe aria-hidden className="size-6 text-accent" />
        {t('language.title')}
      </h1>
      <Section>
        <div role="radiogroup" aria-label={t('language.title')}>
          <Cell
            role="radio"
            aria-checked={!me.locale_chosen}
            label={t('language.telegram')}
            detail={<span lang={me.telegram_locale}>{LANGUAGE_NAMES[me.telegram_locale]}</span>}
            disabled={setLocale.isPending}
            trailing={mark(!me.locale_chosen)}
            onClick={() => {
              choose(null)
            }}
          />
          {LOCALES.map((option) => {
            const chosen = me.locale_chosen && option === me.locale
            return (
              <Cell
                key={option}
                role="radio"
                aria-checked={chosen}
                lang={option}
                label={LANGUAGE_NAMES[option]}
                disabled={setLocale.isPending}
                trailing={mark(chosen)}
                onClick={() => {
                  choose(option)
                }}
              />
            )
          })}
        </div>
      </Section>
      {setLocale.isError && <p className="px-6 text-destructive">{t('error.generic')}</p>}
    </Screen>
  )
}
