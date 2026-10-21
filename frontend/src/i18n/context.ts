import { createContext, type ReactNode } from 'react'

import type { Locale } from './locale'
import type { MessageKey } from './ru'
import type { Values } from './translate'

export interface I18n {
  locale: Locale
  t: (key: MessageKey, values?: Values) => string
  /** Like `t`, with React nodes for placeholders: an amount with its flag in a sentence. */
  tn: (key: MessageKey, nodes: Record<string, ReactNode>) => ReactNode
}

export const I18nContext = createContext<I18n | null>(null)
