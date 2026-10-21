import { Send } from 'lucide-react'

import { resolveLocale } from '../i18n/locale'
import { translate } from '../i18n/translate'

const BOT_URL = 'https://t.me/peertopeerswapbot'

/** Swap needs Telegram; a plain browser gets this and a way there (§1, v1 adds more). */
export function OutsideTelegram() {
  const locale = resolveLocale(null, navigator.language)
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-bg p-6 text-center">
      <img src="/icon.svg" alt="" width={72} height={72} />
      <h1 lang={locale} className="text-xl font-semibold">
        {translate(locale, 'outside.title')}
      </h1>
      <p lang={locale} className="max-w-xs text-hint">
        {translate(locale, 'outside.text')}
      </p>
      <a
        href={BOT_URL}
        lang={locale}
        className="flex items-center gap-2 rounded-xl bg-button px-5 py-3 font-medium text-button-text"
      >
        <Send aria-hidden className="size-5" />
        {translate(locale, 'outside.button')}
      </a>
    </main>
  )
}
