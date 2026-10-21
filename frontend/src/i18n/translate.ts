import { en } from './en'
import { ka } from './ka'
import type { Locale } from './locale'
import { ru, type MessageKey, type Messages } from './ru'

export const DICTIONARIES: Record<Locale, Messages> = { ru, en, ka }

export type Values = Record<string, string | number>

/** Fills `{name}` placeholders. One with no value stays visible rather than vanishing. */
export function format(template: string, values: Values = {}): string {
  return template.replace(/\{(\w+)\}/g, (match, name: string) => {
    const value = values[name]
    return value === undefined ? match : String(value)
  })
}

export function translate(locale: Locale, key: MessageKey, values?: Values): string {
  return format(DICTIONARIES[locale][key], values)
}
