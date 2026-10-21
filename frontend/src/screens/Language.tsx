import { Check, Globe } from 'lucide-react'
import { useNavigate } from 'react-router'

import { useSetLocale } from '../api/me'
import { useI18n } from '../i18n/useI18n'
import { LANGUAGE_NAMES, LOCALES } from '../i18n/locale'
import { hapticSelect } from '../telegram'
import { Cell } from '../ui/Cell'
import { Screen } from '../ui/Screen'
import { Section } from '../ui/Section'

/** Each language in its own script, so it can be found from any of them (ADR-0009). */
export function Language() {
  const { t, locale } = useI18n()
  const setLocale = useSetLocale()
  const navigate = useNavigate()
  return (
    <Screen>
      <h1 className="flex items-center gap-2 px-6 pt-4 text-2xl font-semibold">
        <Globe aria-hidden className="size-6 text-accent" />
        {t('language.title')}
      </h1>
      <Section>
        <div role="radiogroup" aria-label={t('language.title')}>
          {LOCALES.map((option) => (
            <Cell
              key={option}
              role="radio"
              aria-checked={option === locale}
              lang={option}
              label={LANGUAGE_NAMES[option]}
              disabled={setLocale.isPending}
              trailing={
                option === locale ? <Check aria-hidden className="size-5 text-accent" /> : null
              }
              onClick={() => {
                hapticSelect()
                setLocale.mutate(option, { onSuccess: () => void navigate(-1) })
              }}
            />
          ))}
        </div>
      </Section>
      {setLocale.isError && <p className="px-6 text-destructive">{t('error.generic')}</p>}
    </Screen>
  )
}
