import { RotateCw, TriangleAlert } from 'lucide-react'

import { errorMessage } from '../i18n/errors'
import { useI18n } from '../i18n/useI18n'
import { Screen } from '../ui/Screen'

// Trying again won't change these.
const FINAL = new Set(['error.reopen', 'error.link_not_found'])

/** What a failed request leaves on screen: the problem in words, and a way to retry. */
export function Problem({ error, retry }: { error: unknown; retry: () => void }) {
  const { t } = useI18n()
  const message = errorMessage(error)
  return (
    <Screen>
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
        <TriangleAlert aria-hidden className="size-12 text-hint" />
        <h1 className="text-xl font-semibold">{t('error.title')}</h1>
        <p className="text-hint">{t(message)}</p>
        {!FINAL.has(message) && (
          <button
            type="button"
            onClick={retry}
            className="flex items-center gap-2 rounded-xl bg-button px-5 py-3 font-medium text-button-text"
          >
            <RotateCw aria-hidden className="size-5" />
            {t('error.retry')}
          </button>
        )}
      </div>
    </Screen>
  )
}
