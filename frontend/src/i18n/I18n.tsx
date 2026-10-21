import { useEffect, useMemo, type ReactNode } from 'react'

import { I18nContext, type I18n } from './context'
import type { Locale } from './locale'
import { translate } from './translate'

export function I18nProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  const value = useMemo<I18n>(
    () => ({ locale, t: (key, values) => translate(locale, key, values) }),
    [locale],
  )
  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
