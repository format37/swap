import { createContext } from 'react'

import type { Locale } from './locale'
import type { MessageKey } from './ru'
import type { Values } from './translate'

export interface I18n {
  locale: Locale
  t: (key: MessageKey, values?: Values) => string
}

export const I18nContext = createContext<I18n | null>(null)
