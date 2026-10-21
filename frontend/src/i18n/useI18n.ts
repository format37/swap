import { useContext } from 'react'

import { I18nContext, type I18n } from './context'

export function useI18n(): I18n {
  const value = useContext(I18nContext)
  if (!value) throw new Error('useI18n needs an I18nProvider above it')
  return value
}
