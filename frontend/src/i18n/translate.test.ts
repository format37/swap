import { DEFAULT_LOCALE, LOCALES, resolveLocale } from './locale'
import { DICTIONARIES, format, translate } from './translate'

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('dictionaries', () => {
  it('have the same keys and placeholders in every language', () => {
    const reference = DICTIONARIES.ru
    for (const locale of LOCALES) {
      const dictionary = DICTIONARIES[locale]
      expect(Object.keys(dictionary).sort()).toEqual(Object.keys(reference).sort())
      for (const key of Object.keys(reference) as (keyof typeof reference)[]) {
        expect(placeholders(dictionary[key]), `${locale} ${key}`).toEqual(
          placeholders(reference[key]),
        )
      }
    }
  })

  it('leave no string empty', () => {
    for (const locale of LOCALES) {
      for (const text of Object.values(DICTIONARIES[locale])) expect(text.trim()).not.toBe('')
    }
  })
})

describe('format', () => {
  it('fills placeholders and keeps an unknown one visible', () => {
    expect(format('Hi, {name}! {count}', { name: 'Nino', count: 3 })).toBe('Hi, Nino! 3')
    expect(format('Hi, {name}!')).toBe('Hi, {name}!')
  })

  it('translates per locale', () => {
    expect(translate('ka', 'home.hello', { name: 'Nino' })).toBe('გამარჯობა, Nino!')
  })
})

describe('resolveLocale', () => {
  it.each([
    [null, 'ru', 'ru'],
    [null, 'ka', 'ka'],
    [null, 'en-US', 'en'],
    [null, 'RU', 'ru'],
    [null, 'pt-br', 'en'],
    [null, undefined, 'en'],
    ['ka', 'ru', 'ka'],
    ['xx', 'ru', 'ru'],
  ])('chosen %s, Telegram %s → %s', (chosen, languageCode, expected) => {
    expect(resolveLocale(chosen, languageCode)).toBe(expected)
  })

  it('agrees with the api that the fallback is English', () => {
    expect(DEFAULT_LOCALE).toBe('en')
  })
})
